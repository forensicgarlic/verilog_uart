import cocotb
import logging
from cocotb.triggers import Timer, RisingEdge, ClockCycles
from cocotb.clock import Clock
from cocotb.monitors import Monitor, BusMonitor
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
                vec = self.rx
                self.log.debug("value of rx is %s while not receiving" % vec)
                if self.reset_n is not None and self.reset_n == 0: 
                    self._recv({"vec":vec, "reset":True})
                #if presumably receiving a character
                if vec == 0:
                    self.receiving = True
                    #start us out sampling once per period, with a half period delay
                    yield ClockCycles(self.clock, self.baud /2)
                    #may want to sample here to verify it wasn't a glitch falling edge?
                    self._recv({"vec":vec, "reset":False})
            else:
                # wait another period, putting us into actual character bits
                yield ClockCycles(self.clock, self.baud)
                vec = self.rx
                self.log.debug("value of rx is %s while receiving" % vec)
                self._recv({"vec":vec,"reset":False})
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
        yield Timer(1) # gets us past x's on startup. 
        while True:
            yield RisingEdge(self.clock)
            transaction = dict(self.bus.capture())
            rcv = transaction["rcv"]
            data  = transaction["data"]
            if self.in_reset:
                self.log.debug("reset: rcv %s, data %s" % (rcv, data))
                self._recv({"rcv":rcv.integer, "data":data.integer})
            else:
                if rcv == 1:
                    self.log.debug("got something: rcv %s, data %s" % (rcv, data))
                    self._recv({"rcv":rcv.integer, "data":data.integer})
                    
class uart_rx_tb(object):
    def __init__(self, dut):
        self.dut = dut
        self.output_mon = UartRxOMonitor(dut, "o", dut.clk, int(self.dut.BAUD), reset_n=dut.rstn)
        self.input_mon = UartRxMonitor(dut.i_rx, dut.clk, int(self.dut.BAUD), reset_n=dut.rstn, callback=self.rx_model)
        self.output_expected = [{"rcv":0,"data":0}] # necessary because order of calls I think. 
        self.scoreboard = Scoreboard(dut)
        self.scoreboard.add_interface(self.output_mon, self.output_expected)

        self.output_mon.log.setLevel(logging.INFO)
        self.input_mon.log.setLevel(logging.INFO)
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
            self.output_expected.append({"rcv":0,"data":0})
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

                if self.shift >  1<<9:
                    expected = (self.shift >> 1 ) % (1 << 8) 
                    self.output_expected.append({"rcv":1,"data":expected})
                    self.dut._log.debug("model expects uart output %s" % (bin(expected)))
                    self.shift = 0
                else:
                    self.dut._log.info("break mode detected")
            

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
    tb.dut._log.info("k test passed successfully")
    yield Timer(1000000)
    yield tb.rcv_char('K')
    yield Timer(1000000)
    tb.dut._log.info("output expected len %d " % len(tb.output_expected))

@cocotb.test()
def test_2_break(dut):
    """
    break in line, detect / don't spit out chars. 
    """
    tb = uart_rx_tb(dut)
    cocotb.fork(Clock(dut.clk, 1000).start())
    yield tb.reset_dut(10000)

    yield Timer(10000)
    yield RisingEdge(dut.clk)
    tb.dut.i_rx <= 0
    re = RisingEdge(tb.dut.o_rcv)
    result = yield [Timer(5000000), re]

    if result == re:
        raise TestFailure("break condition had output")

    #since the scoreboard is triggered by output, makesure
    #the expected output isn't backed up.
    if len(tb.output_expected) > 0:
        raise TestFailure("model had expected output still")



