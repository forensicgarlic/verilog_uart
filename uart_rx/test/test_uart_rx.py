import cocotb
import logging
from cocotb.triggers import Timer, RisingEdge, ClockCycles
from cocotb.clock import Clock
from cocotb.monitors import Monitor, BusMonitor
from cocotb.scoreboard import Scoreboard
from cocotb.utils import get_sim_time

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
        # where it's interesting in your testbench to have expected output.
        # this probably lines up with when you have actual output. 
        # sometimes that's just every clockcycle, but for uarts, it's often
        # once per baud period, when you know you're receiving / transmitting
        # but on the receive side, you probably don't care about sampling unless
        # you're verifying reset, or your data valid signal is active. 
        yield Timer(1)
        while True:
            if self.receiving == False:
                # if we're not receiving, we need to check for receiving every reset cycle
                yield RisingEdge(self.clock)
                vec = self.rx.value
                self.log.debug("value of rx is %s while not receiving" % vec)
                if self.reset_n is not None and self.reset_n == 0: 
                    self._recv((vec, True))
                #if presumably receiving a character
                if vec == 0:
                    self.receiving = True
                    #start us out sampling once per period, with a half period delay
                    yield ClockCycles(self.clock, self.baud /2)
                    #may want to sample here to verify it wasn't a glitch falling edge? 
            else:
                # wait another period, putting us into actual character bits
                yield ClockCycles(self.clock, self.baud)
                vec = self.rx.value
                self.log.debug("value of rx is %s while receiving" % vec)
                self._recv((vec,False))
                self.count = self.count + 1
                if self.count == 9:
                    self.receiving = False
                    
                
class UartRxOMonitor(BusMonitor):
    _signals = [ "rcv", "data"]
    def __init__(self, entity, name, clock, baud_rate, reset=None, reset_n=None, callback=None, event=None, bus_seperator="_"):
        BusMonitor.__init__(self, entity, name, clock, reset, reset_n, callback, event, bus_seperator)
        self.baud_rate = baud_rate
        self.receiving = False
        
    @cocotb.coroutine
    def _monitor_recv(self):
        yield Timer(1)
        while True:
            yield RisingEdge(self.clock)
            transaction = self.bus.capture()
            transaction_list_values=list(transaction.values())
            rcv, data  = transaction_list_values
            if self.in_reset:
                self.log.debug("reset: rcv %s, data %s" % (rcv, data))
                self._recv((rcv.value, data.value))
            else:
                if rcv == 1:
                    self.log.debug("got something: rcv %s, data %s" % (rcv, data))
                    self._recv((rcv.value, data.value))
                    
class uart_rx_tb(object):
    def __init__(self, dut):
        self.dut = dut
        self.output_mon = UartRxOMonitor(dut, "o", dut.clk, int(self.dut.BAUD), reset_n=dut.rstn)
        self.input_mon = UartRxMonitor(dut.i_rx, dut.clk, int(self.dut.BAUD), reset_n=dut.rstn, callback=self.rx_model)
        self.output_expected = [(0,0)]
        self.scoreboard = Scoreboard(dut)
        self.scoreboard.add_interface(self.output_mon, self.output_expected)

        self.output_mon.log.setLevel(logging.DEBUG)
        self.input_mon.log.setLevel(logging.DEBUG)
        self.dut._log.setLevel(logging.DEBUG)
        self.scoreboard.log.setLevel(logging.INFO)
        
        self.dut.i_rx <= 1
        self.bits = 0
        self.shift = 0
        
    def rx_model(self, transaction):
        rx, in_reset = transaction
        self.dut._log.debug("model called at time %s with transaction %s %s in reset" %(get_sim_time("ns"),rx, in_reset))
        if in_reset:
            self.output_expected.append((0,0))
            self.bits = 0
            self.shift = 0
        else:
            self.bits = (self.bits + 1) % 10
            self.shift = (self.shift << 1) + rx.value
            self.dut._log.debug("bits %d, shift %d, rx.value %d" % (self.bits, self.shift, rx.value))
            if self.bits == 9:
                self.output_expected.pop() #ugh
                self.dut._log.debug("expected output len: %d" % len(self.output_expected.pop()))
                self.output_expected.append((1,self.shift>>2))
                self.dut._log.debug("model expects uart output %d" % (self.shift>>2))
            
            

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
        self.dut._log.debug("output expected length is : %d" % len(self.output_expected))
        # while this is the easiest place to call this, it feels like cheating.
        self.output_expected.append((1,ord(char)))
        for i in range(10):
            self.dut.i_rx <= shift % 2
            shift = shift >> 1
            yield ClockCycles(self.dut.clk, int(self.dut.BAUD))
        

        
# tests:
# detect break condition (or at least, don't spit out rcvs)
# rcv a character
# rcv characters fast
# characters received in reset are ignored
# ignore spurious pulses
# framing error flag? 

@cocotb.test()
def test_1_rcv_a_char(dut):
    """
    basic test, receive a character
    """
    tb = uart_rx_tb(dut)
    tb.dut._log.info("running uartrx test")
    cocotb.fork(Clock(dut.clk, 1000).start())

    yield tb.reset_dut(10000)
    yield Timer(10000)
    yield RisingEdge(dut.clk)
    yield tb.rcv_char('k')
    yield Timer(2000000)
