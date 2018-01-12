import cocotb
from cocotb.triggers import Timer, RisingEdge
from cocotb.result import TestFailure
from cocotb.clock import Clock

CLK_PERIOD = 1000

@cocotb.test()
def initial_access(dut):
    """
    Try accessing the design, setting the Period Parameter
    """
    dut._log.info("Running test!")
    toggled = False
    cocotb.fork(Clock(dut.clk_in, CLK_PERIOD).start())
    dut.clk_en <= 1
    yield RisingEdge(dut.clk_in)
    for cycle in range(10):
        yield RisingEdge(dut.clk_in)
        if int(dut.pulse_out) == 1:
            toggled = True
    dut._log.info("test was run!")
    if not toggled:
        raise TestFailure("clock out did not toggle. There may be a parameter passing issue. PERIOD = %d." % (dut.PERIOD))
    else:  
        dut._log.info("Ok!")

@cocotb.test()
def period(dut):
    """
    verify period matches 10 (value set in makefile)
    """
    PERIOD = int(dut.PERIOD)
    cocotb.fork(Clock(dut.clk_in, CLK_PERIOD).start())
    count = 0
    last_value = 1 # used to catch rising edge for dividers with output greater than 1 clk
    dut.clk_en <= 1
    t = Timer(int(dut.PERIOD) * CLK_PERIOD * 2)
    result = yield [RisingEdge(dut.pulse_out), t]
    if result == t:
        raise TestFailure("output is not toggling")
    for cycle in range(PERIOD*10):
        count = count + 1
        if last_value == 0 and dut.pulse_out == 1:
            if count != PERIOD-1:
                raise TestFailure( "period was incorrect: %d", count)
                count = 0
        last_value = dut.pulse_out
        
        yield RisingEdge(dut.clk_in)
    
@cocotb.test()
def pulse_width(dut):
    """
    verify pulse_width is 1 clk
    """
    t = Timer(int(dut.PERIOD) * CLK_PERIOD*2)
    cocotb.fork(Clock(dut.clk_in, CLK_PERIOD).start())
    dut.clk_en <= 1
    result = yield [RisingEdge(dut.pulse_out), t]
    if result ==t:
        raise TestFailure("output didn't toggle")
    yield RisingEdge(dut.clk_in)
    yield Timer(1)
    if dut.pulse_out == 1:
        raise TestFailure("clk out should have fallen")


@cocotb.test()
def clock_enable(dut):
    """
    verify clock enable turns on and off functionality 
    """
    PERIOD = int(dut.PERIOD)
    
    last_value = 1 # used to catch rising edge for dividers with output greater than 1 clk
    cocotb.fork(Clock(dut.clk_in, CLK_PERIOD).start())
    yield RisingEdge(dut.clk_in)
    for loop in range(2):
        dut.clk_en <= 0
        count = 0
        toggled = False
        yield RisingEdge(dut.clk_in)
        yield RisingEdge(dut.clk_in)
        for cycle in range(PERIOD*10):
            count = count + 1
            #print("pulse out: %s" % dut.pulse_out)
            if dut.pulse_out == 1:
                toggled = True
            
            if last_value == 0 and int(dut.pulse_out) == 1:
                count = 0
                dut._log.info("counter was reset!")
            last_value = dut.pulse_out

            yield RisingEdge(dut.clk_in)

        dut._log.info("count was %d, period was %d",count, PERIOD)
        if count < PERIOD*10:
            raise TestFailure("clock enable didn't prevent output")
        if toggled == True:
            raise TestFailure("output toggled unexpectedly")
        dut.clk_en <= 1
        yield RisingEdge(dut.clk_in)
        count = 0
        for cycle in range(PERIOD*10):
            count = count + 1
            if int(dut.pulse_out) == 1:
                toggled = True
            if last_value == 0 and dut.pulse_out == 1:
                if count != PERIOD-1:
                    count = 0
                    raise TestFailure( "period was incorrect: %d", count)
            last_value = dut.pulse_out

            yield RisingEdge(dut.clk_in)
        if toggled == False:
            raise TestFailure("output did not toggle")
    
