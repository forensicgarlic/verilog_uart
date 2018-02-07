import cocotb
from cocotb.triggers import Timer, RisingEdge
from cocotb.result import TestFailure
from cocotb.clock import Clock
from cocotb.monitors import BusMonitor
from cocotb.drivers import BusDriver
from cocotb.scoreboard import Scoreboard
from cocotb.utils import get_sim_time


class UartMonitor(BusMonitor):
    def __init__(self, entity, name, clock, level, reset=None, reset_n=None, callback=None, event=None, bus_seperator="_"):
        BusMonitor.__init__(self, entity, name, clock, reset, reset_n, callback, event, bus_seperator)
        self.level = level
        self.last_transaction = None
        self.baud_count = 0
        self.baud_rate = 104 # a lot of assumptions happening here.
        self.transmitting = False
        self.bits = 0
        
    @cocotb.coroutine
    def _monitor_recv(self):
        yield Timer(1)
        while True:
            yield RisingEdge(self.clock)
            # we don't really want a transaction every clock cycle --
            # cycle 'accuracy' is hard to pair with flexibility in what a
            # correct design is. 
            # we'd like something closer to every baud cycle, but
            # only when character's are being sent. So, let's have a transaction
            # every clock while reset is active.
            # on a state change after reset goes inactive and not in a ch
            # every baud cycle for a character post that transaction
            if self.transmitting: 
                self.baud_count = (self.baud_count + 1) % self.baud_rate
            transaction = self.bus.capture()
            first =list(transaction.values())
            first = first[0]
            if self.in_reset: 
                for x,y in transaction.items():
                    print("reset time %s -  %s : %s" %(get_sim_time("ns"),x,y))
                self._recv(tuple(transaction.values()))
                self.baud_count = self.baud_rate -1
                self.transmitting = False
                self.bits = 0
            elif self.last_transaction != transaction and not self.transmitting and first == self.level:
                self.transmitting = True
                self.baud_count = self.baud_rate / 2
                for x,y in transaction.items():
                    print("start time %s -  %s : %s" %(get_sim_time("ns"),x,y))
                self.last_transaction = transaction
            elif self.baud_count == 0 and self.transmitting:
                for x,y in transaction.items():
                    print("baud  time %s -  %s : %s" %(get_sim_time("ns"),x,y))
                self._recv(tuple(transaction.values()))
                self.bits = self.bits + 1
                if self.bits == 10:
                    self.transmitting = False
                        
            self.last_transaction = transaction
            
            #for x,y in transaction.items():
            #    print("time %s -  %s : %s" %(get_sim_time("ns"),x,y))
            #self._recv(tuple(transaction.values()))
            #self.last_transaction = transaction
            
class UartOMonitor(UartMonitor):
    _signals = [ "tx", "ready"]
    def __init__(self, entity, name, clock, reset=None, reset_n=None, callback=None, event=None, bus_seperator="_"):
        #looking for tx going down as a start of baud rate checks for character duration
        UartMonitor.__init__(self, entity, name, clock, 0, reset, reset_n, callback, event, bus_seperator)

class UartIMonitor(UartMonitor):
    _signals = [ "start", "data" ]
    def __init__(self, entity, name, clock, reset=None, reset_n=None, callback=None, event=None, bus_seperator="_"):
        #looking for start going up as start of baud rate checks for character duration.
        ### (is start functionality required to toggle low / high? this might end up being an issue. ) 
        UartMonitor.__init__(self, entity, name, clock, 1, reset, reset_n, callback, event, bus_seperator)
        
class UartDriver(BusDriver):
    _signals = [ "start", "data"]
    def __init__(self, entity, name, clock):
        BusDriver.__init__(self, entity, name, clock)

        self.bus.start.setimmediatevalue(0)
        self.bus.data.setimmediatevalue(0)

            
class uart_tb(object):
    def __init__(self, dut):
        self.dut = dut

        self.output_mon = UartOMonitor(dut, "o", dut.clk, reset_n=dut.rstn)
        self.input_mon = UartIMonitor(dut, "i", dut.clk, reset_n=dut.rstn, callback = self.tx_model)
        self.input_drv = UartDriver(dut, "i", dut.clk )
        self.output_expected = [(1,0)] #i don't think this should be necessary... 
        self.scoreboard = Scoreboard(dut)
        #scoreboard is where results are checked. On each transaction of the output_mon, it'll compare against the
        #next transaction in the list output_expected. Output_expected gets updated by the tx_model. tx_model is the
        #callback function of the input monitor. So the expected output gets appended to when the input changes.
        # its not obvious is on the same simulation cycle you can force the tx_model to get called before the
        # scoreboard gets called on 
        self.scoreboard.add_interface(self.output_mon, self.output_expected)
        self.baud_rate = 103
        self.baud_count = 0
        self.shifter = 0
        
    def tx_model(self, transaction):
        # uart header
        if self.input_mon.transmitting: 
            print ("tx model call -- character %d:%d" % (self.input_mon.bits,len(self.output_expected)))
            print (self.output_expected)
            if self.input_mon.bits == 0:
                self.output_expected.pop() #ugh. are we putting in expectations for this cycle, or next? 
                self.output_expected.append((0,0)) #start bit
                self.shifter = transaction[1].integer
                # shift data out 1 bit at a time
                # yielding for end of character, so we don't keep throwing expecteds onto the list. 
                # and adding the start and stop bits
                print ("transaction - %s,%s" %(transaction[0],transaction[1]))
            if self.input_mon.bits < 8:
                self.output_expected.append((self.shifter % 2,0))
                self.shifter = self.shifter >> 1
            else: 
                self.output_expected.append((1,0)) #stop bit

        else:
            print ("tx model call -- idle :%d" % len(self.output_expected))
            self.output_expected.append((1,1))
        
    @cocotb.coroutine
    def reset_dut(self, reset, duration):
        reset <= 0
        yield Timer(duration)
        reset <= 1
        self.dut._log.info("reset complete")

@cocotb.test()
def initial_instance(dut):
    """
    send a character
    """
    tb = uart_tb(dut)
    tb.dut._log.info("running uarttx test")
    cocotb.fork(Clock(dut.clk, 1000).start())

    yield tb.reset_dut(dut.rstn, 10000)

    yield RisingEdge(dut.clk)
    yield Timer(10000)
    yield RisingEdge(dut.clk)
    dut.i_data <= ord('k')
    dut.i_start <= 1
    yield RisingEdge(dut.clk)
    dut.i_start <= 0
    yield Timer(2000000)

#// send a chararacter before ready, and it's ignored
#// change data in middle of send, and it's ignored
#// send multiple character's fast
#// send multile character's slow
