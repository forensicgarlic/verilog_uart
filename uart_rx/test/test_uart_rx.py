
class UartRxMonitor(Monitor):
    """ observe the RX input of a Uart """
    def __init__(self, name, rx, clock, callback=None, event=None):
        self.name = name
        self.rx = rx
        self.clock = clock
        Monitor.__init(self, callback, event)

    @coroutine
    def _monitor_recv(self):
        while True:
            yield RisingEdge(self.clock)
            vec = self.rx.value
            self.rx.log.debug("value of rx is %s" % vec)
            self._recv(vec)
            

class uart_rx_tb(object):
    def __init__(self, dut):
        self.dut = dut
        self.output_mon
        self.input_mon = UartRxMonitor("RX", dut.rx, dut.clock, callback=self.rx_model)
        self.output_expected = [(0,0)]
        self.scoreboard = Scoreboard(dut)
        self.scoreboard.add_interface(self.output_mon, self.output_expected)

    def tx_model(self, transaction):
        pass

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
    tb.dut_log.info("running uartrx test")
    cocotb.fork(Clock(dut.clk, 1000).start())

    yield tb.reset_dut(dut.rstn, 10000)
    yield Timer(10000)
    yield RisingEdge(dut.clk)
    yield tb.rcv_char('k')
    yield Timer(2000000)
