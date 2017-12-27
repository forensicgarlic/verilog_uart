# Code your testbench here
import cocotb
from cocotb.triggers import Timer, RisingEdge
from cocotb.result import TestFailure
from cocotb.clock import Clock

@cocotb.test()
def initial_access(dut):
    """
    Try accessing the design, setting the Period Parameter
    """
    dut._log.info("Running test!")
    toggled = False
    cocotb.fork(Clock(dut.clk_in, 1000).start())
    for cycle in range(10):
        yield RisingEdge(dut.clk_in)
        if dut.clk_out == 1:
            toggled = True
    dut._log.info("test was run!")
    if not toggled:
        raise TestFailure("clock out did not toggle. There is probably a parameter passing issue. PERIOD = %d." % (dut.PERIOD))
    else:  
        dut._log.info("Ok!")

@cocotb.test()
def period(dut):
    """
    verify period matches 10 (value set in makefile)
    """
    PERIOD = int(dut.PERIOD)
    cocotb.fork(Clock(dut.clk_in, 1000).start())
    count = 0
    last_value = 1
    yield RisingEdge(dut.clk_out)
    for cycle in range(PERIOD*10):
        count = count + 1
        if last_value == 0 and dut.clk_out == 1:
            if count < PERIOD-1:
                raise TestFailure( "period was incorrect: %d", count)
                count = 0
        last_value = dut.clk_out
        
        yield RisingEdge(dut.clk_in)
    

        
