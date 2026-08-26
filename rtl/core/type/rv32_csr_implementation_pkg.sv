package rv32_csr_implementation_pkg;

  import rv32_csr_pkg::*;

  // CSR implementations share a uniform request/current-value function API.
  // Individual CSRs intentionally ignore reserved fields or immutable state.
  /* verilator lint_off UNUSEDSIGNAL */
  // Helper
  function automatic csr_rsp_t csr_read_only(input csr_req_t req, input logic [31:0] value);
    csr_rsp_t a;

    a = '0;
    a.read_data = value;
    a.value_candidate = value;
    a.is_legal = !req.write_enable;
    return a;
  endfunction : csr_read_only

  function automatic csr_rsp_t csr_fixed_mrw(input csr_req_t req, input logic [31:0] value);
    csr_rsp_t a;

    a = '0;
    a.read_data = value;
    a.value_candidate = value;
    a.is_legal = 1'b1;
    return a;
  endfunction : csr_fixed_mrw

  // Implementation
  function automatic csr_rsp_t csr_mstatus(input csr_req_t req, input logic [31:0] current);
    csr_rsp_t a;

    a = '0;

    // Architectural read value
    a.read_data = current;
    a.read_data[12:11] = 2'b11;  // fixed MPP: M-mode only

    // Default: preserve state
    a.value_candidate = current;

    if (req.reset_enable) begin
      a.value_candidate = '0;
      a.value_candidate[12:11] = 2'b11;
    end else if (req.write_enable) begin
      // RW fields
      a.value_candidate[3] = req.write_data[3];  // MIE
      a.value_candidate[7] = req.write_data[7];  // MPIE

      // Fixed field
      a.value_candidate[12:11] = 2'b11;
    end

    a.is_legal = 1'b1;
    return a;
  endfunction : csr_mstatus

  function automatic csr_rsp_t csr_mtvec(input csr_req_t req, input logic [31:0] current);
    csr_rsp_t a;

    a = '0;
    a.read_data[31:2] = current[31:2];

    // Default: preserve state
    a.value_candidate = current;

    if (req.reset_enable) begin
      a.value_candidate = '0;
    end else if (req.write_enable) begin
      a.value_candidate = {req.write_data[31:2], 2'b00};
      // Trap mode: Direct Mode
      // TODO: Base addr is deferred
    end

    a.is_legal = 1'b1;
    return a;
  endfunction : csr_mtvec

  function automatic csr_rsp_t csr_mepc(input csr_req_t req, input logic [31:0] current);
    csr_rsp_t a;

    a = '0;
    a.read_data[31:2] = current[31:2];

    // Default: preserve state
    a.value_candidate = current;

    if (req.reset_enable) begin
      a.value_candidate = '0;
    end else if (req.write_enable) begin
      a.value_candidate = {req.write_data[31:2], 2'b00}; // Not required, but enforced to prevent unaligned addr
    end

    a.is_legal = 1'b1;
    return a;
  endfunction : csr_mepc

  function automatic csr_rsp_t csr_mcause(input csr_req_t req, input logic [31:0] current);
    csr_rsp_t a;

    a = '0;
    a.read_data = current;

    // Default: preserve state
    a.value_candidate = current;

    if (req.reset_enable) begin
      a.value_candidate = '0;
    end else if (req.write_enable) begin
      a.value_candidate = req.write_data; // Transferred by trap controller
    end

    a.is_legal = 1'b1;
    return a;
  endfunction : csr_mcause

  function automatic csr_rsp_t csr_mtval(input csr_req_t req, input logic [31:0] current);
    csr_rsp_t a;

    a = '0;
    a.read_data = current;

    // Default: preserve state
    a.value_candidate = current;

    if (req.reset_enable) begin
      a.value_candidate = '0;
    end else if (req.write_enable) begin
      a.value_candidate = req.write_data;  // Transferred by trap controller
    end

    a.is_legal = 1'b1;
    return a;
  endfunction : csr_mtval

  // TODO: verify specification compliances
  function automatic csr_rsp_t csr_mie(input csr_req_t req, input logic [31:0] current);
    csr_rsp_t a;

    a = '0;
    a.read_data[7] = current[7];
    a.value_candidate[7] = current[7];

    if (req.reset_enable) begin
      a.value_candidate = '0;
    end else if (req.write_enable) begin
      a.value_candidate[7] = req.write_data[7];
    end

    a.is_legal = 1'b1;
    return a;
  endfunction : csr_mie

  function automatic csr_rsp_t csr_mip(input csr_req_t req, input logic [31:0] current);
    csr_rsp_t a;

    a = '0;
    a.read_data[7] = current[7];
    a.value_candidate[7] = current[7];

    if (req.reset_enable) begin
      a.value_candidate = '0;
    end

    a.is_legal = 1'b1;
    return a;
  endfunction : csr_mip

  function automatic csr_rsp_t csr_mstatush(input csr_req_t req, input logic [31:0] current);
    return csr_fixed_mrw(req, 32'b0);
  endfunction : csr_mstatush

  function automatic csr_rsp_t csr_mscratch(input csr_req_t req, input logic [31:0] current);
    csr_rsp_t a;

    a = '0;
    a.read_data = current;
    a.value_candidate = current;

    if (req.reset_enable) begin
      a.value_candidate = '0;
    end else if (req.write_enable) begin
      a.value_candidate = req.write_data;
    end

    a.is_legal = 1'b1;
    return a;
  endfunction : csr_mscratch

  function automatic csr_rsp_t csr_misa(input csr_req_t req, input logic [31:0] current);
    return csr_fixed_mrw(req, 32'h4000_0100);
    // Machine XLEN = 2'b01 (32-bit)
    // Supported Extension = Only RV32I
  endfunction : csr_misa

  function automatic csr_rsp_t csr_mvendorid(input csr_req_t req, input logic [31:0] current);
    return csr_read_only(req, 32'h0000_0000); // Not Implemented
  endfunction : csr_mvendorid

  function automatic csr_rsp_t csr_marchid(input csr_req_t req, input logic [31:0] current);
    return csr_read_only(req, 32'h0000_0000); // Not Implemented
  endfunction : csr_marchid

  function automatic csr_rsp_t csr_mimpid(input csr_req_t req, input logic [31:0] current);
    return csr_read_only(req, 32'h0000_0000); // Not Implemented
  endfunction : csr_mimpid

  function automatic csr_rsp_t csr_mhartid(input csr_req_t req, input logic [31:0] current);
    return csr_read_only(req, 32'h0000_0000); // Single hart, fixed 0
  endfunction : csr_mhartid

  function automatic csr_rsp_t csr_mconfigptr(input csr_req_t req, input logic [31:0] current);
    return csr_read_only(req, 32'h0000_0000); // No Config provided
  endfunction : csr_mconfigptr

  /* verilator lint_on UNUSEDSIGNAL */

endpackage : rv32_csr_implementation_pkg
