COCOTB?=$(shell pwd)/../
export COCOTB

MODS := div/test \
	uart_tx/test \
	uart_rx/test \

.PHONY: $(MODS)

all: $(MODS)

$(MODS):
	@cd $@ && $(MAKE)

clean:
	$(foreach TEST, $(MODS), $(MAKE) -C $(TEST) clean;)
