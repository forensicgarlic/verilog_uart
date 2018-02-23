import logging
import cocotb
from cocotb.triggers import Timer, RisingEdge
from cocotb.result import TestFailure
from cocotb.clock import Clock
from cocotb.monitors import BusMonitor
from cocotb.drivers import BusDriver
from cocotb.scoreboard import Scoreboard
from cocotb.utils import get_sim_time


class UartMonitor(BusMonitor):
    def __init__(self, entity, name, clock, baud_rate, trigger_transmit_state, reset=None, reset_n=None, callback=None, event=None, bus_seperator="_"):
        BusMonitor.__init__(self, entity, name, clock, reset, reset_n, callback, event, bus_seperator)
        self.tts = trigger_transmit_state
        self.last_transaction = None
        self.baud_count = 0
        self.baud_rate = baud_rate
        self.transmitting = False
        self.bits = 0
        self.start_second = 0
        
    @cocotb.coroutine
    def _monitor_recv(self):
        yield Timer(1)
        while True:
            yield RisingEdge(self.clock)
            if self.transmitting: 
                self.baud_count = (self.baud_count + 1) % self.baud_rate
            transaction = self.bus.capture()
            transaction_list_values =list(transaction.values())
            first = transaction_list_values[0]
            second = transaction_list_values[1]
            if self.in_reset: 
                for x,y in transaction.items():
                    self.log.debug("reset time %s -  %s : %s" %(get_sim_time("ns"),x,y))
                self._recv(tuple(transaction.values()))
                self.baud_count = self.baud_rate -1
                self.transmitting = False
                self.bits = 0
            elif self.tts(self,transaction, first):
                self.transmitting = True
                self.bits = 0
                self.start_second = second
                self.baud_count = self.baud_rate / 2
                for x,y in transaction.items():
                    self.log.debug("start time %s -  %s : %s" %(get_sim_time("ns"),x,y))
                self.last_transaction = transaction
            elif self.baud_count == 0 and self.transmitting:
                for x,y in transaction.items():
                    self.log.debug("baud  time %s -  %s : %s" %(get_sim_time("ns"),x,y))
                self._recv(tuple(transaction.values()))
                self.bits = self.bits + 1
                if self.bits == 10:
                    self.transmitting = False
            self.last_transaction = transaction
            
class UartOMonitor(UartMonitor):
    _signals = [ "tx", "ready"]

    def __init__(self, entity, name, clock, baud_rate, reset=None, reset_n=None, callback=None, event=None, bus_seperator="_"):
        #looking for tx going down as a start of baud rate checks for character duration
        def trigger_transmit_state(self,transaction, first):
            return self.last_transaction != transaction and not self.transmitting and first == 0
        UartMonitor.__init__(self, entity, name, clock, baud_rate, trigger_transmit_state, reset, reset_n, callback, event, bus_seperator)

        
class UartIMonitor(UartMonitor):
    _signals = [ "start", "data" ]


    def __init__(self, entity, name, clock, baud_rate, reset=None, reset_n=None, callback=None, event=None, bus_seperator="_"):
        #looking for start set high as start of baud rate checks for character duration.
        def trigger_transmit_state(self, transaction, first):
            return not self.transmitting and first == 1
        UartMonitor.__init__(self, entity, name, clock, baud_rate, trigger_transmit_state, reset, reset_n, callback, event, bus_seperator)
        
class UartDriver(BusDriver):
    _signals = [ "start", "data"]
    def __init__(self, entity, name, clock):
        BusDriver.__init__(self, entity, name, clock)
        self.bus.start.setimmediatevalue(0)
        self.bus.data.setimmediatevalue(0)
            
class uart_tx_tb(object):
    def __init__(self, dut):
        self.dut = dut
        self.output_mon = UartOMonitor(dut, "o", dut.clk, int(self.dut.BAUD), reset_n=dut.rstn)
        self.input_mon = UartIMonitor(dut, "i", dut.clk, int(self.dut.BAUD), reset_n=dut.rstn, callback = self.tx_model)
        self.input_drv = UartDriver(dut, "i", dut.clk ) #unused?
        self.output_expected = [(1,0)] #i don't think this should be necessary... 
        self.scoreboard = Scoreboard(dut)

        #self.output_mon.log.setLevel(logging.DEBUG)
        
        #scoreboard is where results are checked. On each transaction of the output_mon, it'll compare against the
        #next transaction in the list output_expected. Output_expected gets updated by the tx_model. tx_model is the
        #callback function of the input monitor. So the expected output gets appended to when the input changes.
        # its not obvious if on the same simulation cycle you can force the tx_model to get called before the
        # scoreboard gets called on 
        self.scoreboard.add_interface(self.output_mon, self.output_expected)
        self.baud_rate = int(self.dut.BAUD) -1
        self.baud_count = 0
        self.shifter = 0
        
    def tx_model(self, transaction):
        # shift data (transaction second field) out 1 bit at a time
        # at the baud rate
        # adding start and stop bits to the expected values. 
        if self.input_mon.transmitting: 
            #print ("tx model call -- character %d:%d" % (self.input_mon.bits,len(self.output_expected)))
            #print (self.output_expected)
            if self.input_mon.bits == 0:
                self.output_expected.pop() #ugh. are we putting in expectations for this cycle, or next? 
                self.output_expected.append((0,0)) #start bit
                self.shifter = self.input_mon.start_second 
                #print ("transaction - %s,%s" %(transaction[0],transaction[1]))
            if self.input_mon.bits < 8:
                self.output_expected.append((self.shifter % 2,0))
                self.shifter = self.shifter >> 1
            else: 
                self.output_expected.append((1,0)) #stop bit
        else:
            #print ("tx model call -- idle :%d" % len(self.output_expected))
            if self.input_mon.in_reset:
                self.output_expected.append((1,0))
            else:
                self.output_expected.append((1,1))
        
    @cocotb.coroutine
    def reset_dut(self, reset, duration):
        reset <= 0
        yield Timer(duration)
        reset <= 1
        self.dut._log.info("reset complete")

    @cocotb.coroutine
    def set_char(self, char):
        yield RisingEdge(self.dut.clk)
        self.dut.i_data <= ord(char)
        self.dut.i_start <= 1
        yield RisingEdge(self.dut.clk)
        self.dut.i_start <= 0
        self.dut._log.info("sent char %s" % char)
        
@cocotb.test()
def test_1_send_a_char(dut):
    """
    send a character
    """
    tb = uart_tx_tb(dut)
    tb.dut._log.info("running uarttx test")
    cocotb.fork(Clock(dut.clk, 1000).start())

    yield tb.reset_dut(dut.rstn, 10000)

    yield RisingEdge(dut.clk)
    yield Timer(10000)
    yield tb.set_char('k')
    yield Timer(2000000)

@cocotb.test()
def test_2_ignore_ready(dut):
    """
    change data in middle of send, and it's ignored
    """
    tb = uart_tx_tb(dut)
    cocotb.fork(Clock(dut.clk, 1000).start())

    yield tb.reset_dut(dut.rstn, 10000)

    yield Timer(10000)
    yield tb.set_char('K')

    my_char = ord('O')
    for i in range(15):
        yield Timer(50000)
        if dut.o_ready == 1:
            raise TestFailure("ready was active unexpectently. Check the baud rate, and update the test to know it. ")
        yield tb.set_char(chr(my_char + i))
    yield Timer(2000000)

@cocotb.test()
def test_3_send_in_reset(dut):
    """ 
    send a chararacter before ready, and it's ignored
    """
    tb = uart_tx_tb(dut)
    cocotb.fork(Clock(dut.clk, 1000).start())

    cocotb.fork(tb.reset_dut(dut.rstn,20000))

    yield Timer(10000)
    if dut.o_ready == 1:
        raise TestFailure("ready was active unexpectently. Check the reset control. ")

    yield tb.set_char('a')

    yield Timer(1000000)

@cocotb.test()
def test_4_send_chars_fast(dut):
    """
     send multiple character's fast
    """
    tb = uart_tx_tb(dut)
    cocotb.fork(Clock(dut.clk, 1000).start())
    yield tb.reset_dut(dut.rstn, 10000)
    yield Timer(10000)
    my_char = ord('C')
    for i in range(10):
        yield tb.set_char(chr(my_char + i))
        yield RisingEdge(dut.o_ready)
                       
@cocotb.test()
def test_5_start_ignores_ready(dut):
    """
    Normally, start would only be high for a cycle. But with weird input, 
    Start might just stay high. Verify test and dut still works if that 
    happens. 
    """

    tb = uart_tx_tb(dut)
    cocotb.fork(Clock(dut.clk, 1000).start())
    yield tb.reset_dut(dut.rstn, 10000)
    yield Timer(10000)
    my_char = ord('c')
    for i in range(3):
        yield RisingEdge(dut.clk)
        dut.i_data <= my_char + i
        dut.i_start <= 1
        dut._log.info("sent char %s" % chr(my_char+i))
        
        yield Timer(1055000)
