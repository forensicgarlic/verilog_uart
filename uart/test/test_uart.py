import cocotb
import logging
from cocotb.triggers import Timer, RisingEdge, ClockCycles
from cocotb.clock import Clock
from cocotb.monitors import Monitor, BusMonitor
from cocotb.drivers import BusDriver
from cocotb.scoreboard import Scoreboard
from cocotb.utils import get_sim_time
from cocotb.result import TestFailure

class UartRxMonitor(Monitor):
    """ observe the RX input of a Uart """
    def __init__(self, rx, clock, baud, reset_n=None, callback=None, event=None):
        self.clock = clock
        self.rx = rx
        self.baud = baud
        self.receiving = False
        self.buff = 0
        self.count = 0
        self.reset_n = reset_n
        Monitor.__init__(self, callback, event)

    @cocotb.coroutine
    def _monitor_recv(self):
        # this coroutine's responsibility is to sample at the points
        # where it's interesting in your testbench to know what the input was,
        # presumably because it'll have an effect on expected output.
        # sometimes that's just every clockcycle, but for uarts, it's often
        # once per baud period, when you know you're receiving / transmitting
        yield Timer(1)
        while True:
            if self.receiving == False:
                # if we're not receiving, we need to check for receiving every reset cycle
                yield RisingEdge(self.clock)
                vec = self.rx
                self.log.debug("value of rx is %s while not receiving" % vec)
                if self.reset_n is not None and self.reset_n == 0: 
                    self._recv({"vec":vec, "reset":True})
                #if presumably receiving a character
                elif vec == 0:
                    self.receiving = True
                    self.count = 0
                    #start us out sampling once per period, with a half period delay
                    yield ClockCycles(self.clock, self.baud /2)
                    #we want to sample here to verify it wasn't a glitch falling edge
                    self._recv({"vec":vec, "reset":False})
            else:
                # wait another period, putting us into actual character bits
                yield ClockCycles(self.clock, self.baud)
                vec = self.rx
                self.log.debug("value of rx is %s while receiving" % vec)
                self._recv({"vec":vec,"reset":False})
                self.count = self.count + 1 
                if self.count == 9: #is a magic number necessary? 
                    self.receiving = False
                    
                
class UartRxOMonitor(BusMonitor):
    _signals = [ "rx_data_valid", "rx_data"]
    def __init__(self, entity, name, clock, baud_rate, reset=None, reset_n=None, callback=None, event=None, bus_seperator="_"):
        BusMonitor.__init__(self, entity, name, clock, reset, reset_n, callback, event, bus_seperator)
        self.baud_rate = baud_rate
        self.receiving = False
        
    @cocotb.coroutine
    def _monitor_recv(self):
        yield Timer(1) # gets us past x's on startup. 
        while True:
            yield RisingEdge(self.clock)
            transaction = dict(self.bus.capture())
            rcv = transaction["rx_data_valid"]
            data  = transaction["rx_data"]
            if self.in_reset:
                self.log.debug("reset: rx_valid %s, rx_data %s" % (rcv, data))
                self._recv({"rx_data_valid":rcv.integer, "rx_data":data.integer})
            else:
                if rcv == 1:
                    self.log.debug("got something: rx_valid %s, rx_data %s" % (rx_data_valid, rx_data))
                    self._recv({"rx_data_valid":rcv.integer, "rx_data":data.integer})

class UartTxMonitor(BusMonitor):
    def __init__(self, entity, name, clock, baud_rate, trigger_transmit_state, reset=None, reset_n=None, callback=None, event=None, bus_seperator="_"):
        BusMonitor.__init__(self, entity, name, clock, reset, reset_n, callback, event, bus_seperator)
        self.tts = trigger_transmit_state
        self.last_transaction = None
        self.baud_count = 0
        self.baud_rate = baud_rate
        self.transmitting = False
        self.bits = 0
        self.start_data = 0
        
    @cocotb.coroutine
    def _monitor_recv(self):
        yield Timer(1)
        while True:
            yield RisingEdge(self.clock)
            if self.transmitting: 
                self.baud_count = (self.baud_count + 1) % self.baud_rate
            transaction = dict(self.bus.capture())
            if self.in_reset: 
                for x,y in transaction.items():
                    self.log.debug("reset time %s -  %s : %s" %(get_sim_time("ns"),x,y))
                self._recv(transaction)
                self.baud_count = self.baud_rate -1
                self.transmitting = False
                self.bits = 0
            elif self.tts(self,transaction):
                self.transmitting = True
                self.bits = 0
                if 'data' in transaction:
                    self.start_data = transaction['rx_data']
                self.baud_count = self.baud_rate / 2
                for x,y in transaction.items():
                    self.log.debug("start time %s -  %s : %s" %(get_sim_time("ns"),x,y))
                self.last_transaction = transaction
            elif self.baud_count == 0 and self.transmitting:
                for x,y in transaction.items():
                    self.log.debug("baud  time %s -  %s : %s" %(get_sim_time("ns"),x,y))
                self._recv(transaction)
                self.bits = self.bits + 1
                if self.bits == 10:
                    self.transmitting = False
            self.last_transaction = transaction
            
class UartTxOMonitor(UartTxMonitor):
    _signals = [ "tx", "tx_ready"]

    def __init__(self, entity, name, clock, baud_rate, reset=None, reset_n=None, callback=None, event=None, bus_seperator="_"):
        #looking for tx going down as a start of baud rate checks for character duration
        def trigger_transmit_state(self,transaction):
            return self.last_transaction != transaction and not self.transmitting and transaction['tx'] == 0
        UartTxMonitor.__init__(self, entity, name, clock, baud_rate, trigger_transmit_state, reset, reset_n, callback, event, bus_seperator)

        
class UartTxIMonitor(UartTxMonitor):
    _signals = [ "tx_start", "tx_data" ]

    def __init__(self, entity, name, clock, baud_rate, reset=None, reset_n=None, callback=None, event=None, bus_seperator="_"):
        #looking for start set high as start of baud rate checks for character duration.
        def trigger_transmit_state(self, transaction):
            return not self.transmitting and transaction['start'] == 1
        UartTxMonitor.__init__(self, entity, name, clock, baud_rate, trigger_transmit_state, reset, reset_n, callback, event, bus_seperator)
        
class UartTxDriver(BusDriver):
    _signals = [ "tx_start", "tx_data"]
    def __init__(self, entity, name, clock):
        BusDriver.__init__(self, entity, name, clock)
        self.bus.start.setimmediatevalue(0)
        self.bus.data.setimmediatevalue(0)

                    
class uart_tb(object):
    def __init__(self, dut):
        self.dut = dut
        self.output_rx_mon = UartRxOMonitor(dut, "o", dut.clk, int(self.dut.BAUD), reset_n=dut.rstn)
        self.input_rx_mon = UartRxMonitor(dut.i_rx, dut.clk, int(self.dut.BAUD), reset_n=dut.rstn, callback=self.rx_model)
        self.output_expected = [{"rx_data_valid":0,"rx_data":0}] # necessary because order of calls  
        self.scoreboard = Scoreboard(dut)
        self.scoreboard.add_interface(self.output_rx_mon, self.output_expected)

        self.output_rx_mon.log.setLevel(logging.INFO)
        self.input_rx_mon.log.setLevel(logging.INFO)
        self.dut._log.setLevel(logging.INFO)
        self.scoreboard.log.setLevel(logging.INFO)
        
        self.dut.i_rx <= 1
        self.bits = 0
        self.shift = 0
        self.last_reset = False
        
    def rx_model(self, transaction):
        rx = transaction["vec"]
        in_reset = transaction["reset"]
        self.dut._log.debug("model called at time %s with transaction %s %s in reset" %(get_sim_time("ns"),rx, in_reset))
        if in_reset:
            self.dut._log.debug("output expected length: %d" % len(self.output_expected))
            self.output_expected.append({"rx_data_valid":0,"rx_data":0})
            self.bits = 0
            self.shift = 0
            self.last_reset = True
        else:
            self.shift = self.shift + (int(rx) << self.bits)
            self.dut._log.debug("bits %d, shift %x, rx %d" % (self.bits, self.shift, rx))
            self.bits = (self.bits + 1) % 10
            if self.bits == 0:
                len_oe = len(self.output_expected)
                if len_oe == 1 and self.last_reset:
                    self.last_reset = False
                    popped = self.output_expected.pop() #ugh
                    self.dut._log.warning("popping data from output expected: %r" % popped)
                elif len_oe > 1:
                    self.dut._log.error("some nonsense with output expected happened")
                self.dut._log.debug("expected output len: %d" % len(self.output_expected))

                if self.shift >=  (1<<9) :
                    expected = (self.shift >> 1 ) % (1 << 8) 
                    self.output_expected.append({"rx_data_valid":1,"rx_data":expected})
                    self.dut._log.debug("model expects uart output %s" % (bin(expected)))
                else:
                    self.dut._log.info("break mode detected")

                self.shift = 0

    @cocotb.coroutine
    def reset_dut(self, duration):
        self.dut.rstn <= 0
        yield Timer(duration)
        self.dut.rstn <= 1
        self.dut._log.info("reset complete")

    @cocotb.coroutine
    def rcv_char(self, char):
        shift = (ord(char)*2 )+ 2**9
        self.dut._log.info("receiving char %s (%x) as %x" %(char, ord(char), shift))
        yield RisingEdge(self.dut.clk)
        for i in range(10):
            self.dut.i_rx <= shift % 2
            shift = shift >> 1
            yield ClockCycles(self.dut.clk, int(self.dut.BAUD))
        
    @cocotb.coroutine
    def set_char(self, char):
        yield RisingEdge(self.dut.clk)
        self.dut.i_data <= ord(char)
        self.dut.i_start <= 1
        yield RisingEdge(self.dut.clk)
        self.dut.i_start <= 0
        self.dut._log.info("sent char %s" % char)

        
@cocotb.test()
def test_1_rcv_and_xmt(dut):
    """
    basic test, receive and xmt a char
    """
    tb = uart_tb(dut)
    tb.dut._log.info("running uart test rcv and xmt")
    cocotb.fork(Clock(dut.clk, 1000).start())

    yield tb.reset_dut(10000)
    yield Timer(10000)
    yield RisingEdge(dut.clk)
    yield tb.rcv_char('k')
    tb.dut._log.info("k test passed successfully")
    yield Timer(1000000)
    yield tb.rcv_char('K')
    yield Timer(1000000)
    tb.dut._log.info("output expected len %d " % len(tb.output_expected))

@cocotb.test()
def test_2_xmt_and_rcv(dut):
    """
    simple test to loopback xmt and rcv  
    """
    tb = uart_tb(dut)
    cocotb.fork(Clock(dut.clk, 1000).start())
    yield tb.reset_dut(10000)

    yield Timer(10000)
    yield RisingEdge(dut.clk)
    tb.dut.i_rx <= 0
    re = RisingEdge(tb.dut.o_rx_data_valid)
    result = yield [Timer(5000000), re]

    if result == re:
        raise TestFailure("break condition had output")

    #since the scoreboard is triggered by output, makesure
    #the expected output isn't backed up.
    if len(tb.output_expected) > 0:
        raise TestFailure("model had expected output still")

