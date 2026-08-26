interface rv32_mem_if;

  // The core-only lint top deliberately leaves requester interfaces unbound.
  // Connectivity is checked by integration tops with concrete responders.
  /* verilator lint_off UNUSEDSIGNAL */
  /* verilator lint_off UNDRIVEN */
  logic        req;
  logic        we;
  logic [31:0] addr;
  logic [31:0] wdata;
  logic [ 3:0] wstrb;

  logic        ready;
  logic [31:0] rdata;
  logic        err;
  /* verilator lint_on UNDRIVEN */
  /* verilator lint_on UNUSEDSIGNAL */

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

  modport responder(
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
