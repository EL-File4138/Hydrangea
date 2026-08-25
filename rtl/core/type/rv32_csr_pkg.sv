package rv32_csr_pkg;

  typedef enum logic [2:0] {
    RW,
    RO,
    WPRI,
    WARL,
    WLRL
  } csr_sem_t;

  typedef enum logic [11:0] {
    MSTATUS    = 12'h300,
    MISA       = 12'h301,
    MIE        = 12'h304,
    MTVEC      = 12'h305,
    MSTATUSH   = 12'h310,
    MSCRATCH   = 12'h340,
    MEPC       = 12'h341,
    MCAUSE     = 12'h342,
    MTVAL      = 12'h343,
    MIP        = 12'h344,
    MVENDORID  = 12'hF11,
    MARCHID    = 12'hF12,
    MIMPID     = 12'hF13,
    MHARTID    = 12'hF14,
    MCONFIGPTR = 12'hF15
  } csr_addr_t;

  typedef enum int unsigned {
    IDX_MSTATUS,
    IDX_MISA,
    IDX_MIE,
    IDX_MTVEC,
    IDX_MSTATUSH,
    IDX_MSCRATCH,
    IDX_MEPC,
    IDX_MCAUSE,
    IDX_MTVAL,
    IDX_MIP,
    IDX_MVENDORID,
    IDX_MARCHID,
    IDX_MIMPID,
    IDX_MHARTID,
    IDX_MCONFIGPTR,
    NUM_CSRS
  } csr_idx_t;

  typedef struct packed {
    logic        wr_en;
    logic        rst_en;
    logic [31:0] wdata;
  } csr_req_t;

  typedef struct packed {
    logic        legal;
    logic [31:0] rdata;
    logic [31:0] next;

    csr_idx_t cell_idx;
    logic     cell_valid;
  } csr_rsp_t;

  typedef struct packed {
    logic        en;
    logic [11:0] addr;
    logic [31:0] wdata;
  } csr_write_t;
endpackage : rv32_csr_pkg
