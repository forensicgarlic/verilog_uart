# verilog_uart
verilog uart tested on the lattice ice40 and simulated using cocotb receiving 8 bit streams, inspired by Obijuan / open-fpga-verilog-tutorial and ZipCPU / wbuart32

#Bootstrapping the verilog uart repo

    sudo apt install git

[Connecting to github with ssh](https://help.github.com/articles/connecting-to-github-with-ssh/)

    ssh-keygen

copy the public key results into your github account

    git clone git@github.com:forensicgarlic/verilog_uart.git

Install docker according to [this](https://docs.docker.com/install/linux/docker-ce/ubuntu/#os-requirements)

build the docker to run things: 

    docker build -t vu .

run the docker image interactively

    docker run -it bash --rm

-i (interactively)
-t (pseudo tty)
--rm (remove container when done) 
-v <local directory>:<name to use in docker> (allows docker to access <local directory> at <name to use in docker> location

    cd verilog_uart
    run make
    make 

if one of the tests locks up, It might be cocotb's fault. make sure you're using my branch of cocotb dls_own_hands for now. 

