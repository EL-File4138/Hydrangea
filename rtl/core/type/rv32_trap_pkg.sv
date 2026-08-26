package rv32_trap_pkg;

  typedef enum logic [30:0] {
    // synchronous exceptions
    EXC_INST_ADDR_MISALIGNED  = 31'd0,
    EXC_INST_ACCESS_FAULT     = 31'd1,
    EXC_ILLEGAL_INST          = 31'd2,
    EXC_BREAKPOINT            = 31'd3,
    EXC_LOAD_ADDR_MISALIGNED  = 31'd4,
    EXC_LOAD_ACCESS_FAULT     = 31'd5,
    EXC_STORE_ADDR_MISALIGNED = 31'd6,
    EXC_STORE_ACCESS_FAULT    = 31'd7,

    EXC_ECALL_U = 31'd8,
    EXC_ECALL_M = 31'd11
  } exception_code_e;

  typedef enum logic [30:0] {
    INT_MACHINE_SOFTWARE = 31'd3,
    INT_MACHINE_TIMER    = 31'd7,
    INT_MACHINE_EXTERNAL = 31'd11
  } interrupt_code_e;

  typedef struct packed {
    logic        is_valid;
    logic        is_interrupt;
    logic [30:0] code;
    logic [31:0] tval;
  } trap_req_t;

  function automatic trap_req_t make_exception(input logic [30:0] code, input logic [31:0] tval);
    trap_req_t trap;

    trap.is_valid     = 1'b1;
    trap.is_interrupt = 1'b0;
    trap.code      = code;
    trap.tval      = tval;

    return trap;
  endfunction : make_exception

endpackage : rv32_trap_pkg
