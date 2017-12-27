FROM python

# prerequisites. 
RUN apt-get update && apt-get install -y gperf flex bison

#icarus 10.2
RUN wget ftp://icarus.com/pub/eda/verilog/v10/verilog-10.2.tar.gz ; \
tar xvf verilog-10.2.tar.gz  ; \
cd verilog-10.2 ; \
./configure ; \
make  ; \
make install

