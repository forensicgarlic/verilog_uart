import cocotb
from cocotb.triggers import Timer, RisingEdge
from cocotb.result import TestFailure
from cocotb.clock import Clock

@cocotb.test()
def initial_instance(dut):
    """
    Basically, the design compiles
    """
    dut._log.info("running uarttx test")
    cocotb.fork(Clock(dut.clk, 1000).start())

    yield RisingEdge(dut.clk)

    
