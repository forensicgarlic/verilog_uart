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
    dut.clk_en = 1
    yield RisingEdge(dut.clk_in)
    for cycle in range(10):
        yield RisingEdge(dut.clk_in)
        if int(dut.pulse_out) == 1:
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
    last_value = 1 # used to catch rising edge for dividers with output greater than 1 clk
    dut.clk_en = 1
    yield RisingEdge(dut.pulse_out)
    for cycle in range(PERIOD*10):
        count = count + 1
        if last_value == 0 and dut.pulse_out == 1:
            if count < PERIOD-1:
                raise TestFailure( "period was incorrect: %d", count)
                count = 0
        last_value = dut.pulse_out
        
        yield RisingEdge(dut.clk_in)
    
@cocotb.test()
def pulse_width(dut):
    """
    verify pulse_width is 1 clk
    """
    cocotb.fork(Clock(dut.clk_in, 1000).start())
    yield RisingEdge(dut.clk_in)
    raise TestFailure("not yet implemented")


@cocotb.test()
def clock_enable(dut):
    """
    verify clock enable turns on and off functionality 
    """
    cocotb.fork(Clock(dut.clk_in, 1000).start())
    yield RisingEdge(dut.clk_in)
    raise TestFailure("not yet implemented")

