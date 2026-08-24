interface rv32_mem_if;

  logic        req;
  logic        we;
  logic [31:0] addr;
  logic [31:0] wdata;
  logic [ 3:0] wstrb;

  logic        ready;
  logic [31:0] rdata;
  logic        err;

  modport requester(
      output req,
      output we,
      output addr,
      output wdata,
      output wstrb,

      input ready,
      input rdata,
      input err
  );

  modport respondend(
      input req,
      input we,
      input addr,
      input wdata,
      input wstrb,

      output ready,
      output rdata,
      output err
  );

endinterface : rv32_mem_if
