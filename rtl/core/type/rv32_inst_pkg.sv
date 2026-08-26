package rv32_inst_pkg;

  typedef enum logic [2:0] {
    INST_FORMAT_R,
    INST_FORMAT_I,
    INST_FORMAT_S,
    INST_FORMAT_B,
    INST_FORMAT_U,
    INST_FORMAT_J
  } inst_format_e;

  typedef enum logic [1:0] {
    MEM_WIDTH_BYTE = 2'b00,
    MEM_WIDTH_HALF = 2'b01,
    MEM_WIDTH_WORD = 2'b10
  } mem_width_e;

  typedef enum logic {
    LOAD_SIGNED   = 0,
    LOAD_UNSIGNED = 1
  } load_signedness_e;

  typedef enum logic [3:0] {  // {func7[5], funct3}
     ALU_ADD  = 4'b0000,
     ALU_SUB  = 4'b1000,
     ALU_SLL  = 4'b0001,
     ALU_SLT  = 4'b0010,
     ALU_SLTU = 4'b0011,
     ALU_XOR  = 4'b0100,
     ALU_SRL  = 4'b0101,
     ALU_SRA  = 4'b1101,
     ALU_OR   = 4'b0110,
     ALU_AND  = 4'b0111
  } alu_op_e;
  // op == 19: I, op == 51: R;
  // Micro op only diff by func

  typedef enum logic [3:0] {  // {op[5], funct3}
     LSU_LB  = 4'b0000,
     LSU_LH  = 4'b0001,
     LSU_LW  = 4'b0010,
     LSU_LBU = 4'b0100,
     LSU_LHU = 4'b0101,
     LSU_SB  = 4'b1000,
     LSU_SH  = 4'b1001,
     LSU_SW  = 4'b1010
  } lsu_op_e;
  // op == 3: I, op == 35: S;
  // mem_op_width extracts [1:0];
  // load_sign extracts [2];
  // Load/Store extracts [3]

  typedef enum logic [2:0] {
     CONTROL_BEQ  = 3'b000,
     CONTROL_BNE  = 3'b001,
     CONTROL_BLT  = 3'b100,
     CONTROL_BGE  = 3'b101,
     CONTROL_BLTU = 3'b110,
     CONTROL_BGEU = 3'b111,
     CONTROL_JALR = 3'b010,
     CONTROL_JAL  = 3'b011
  } control_op_e;
  // op == 99: B, op == 103: I, op == 111: J;

  typedef enum logic [2:0] {  // funct3
    CSR_SYS = 3'b000,
    CSR_RW  = 3'b001,
    CSR_RS  = 3'b010,
    CSR_RC  = 3'b011,
    CSR_RWI = 3'b101,
    CSR_RSI = 3'b110,
    CSR_RCI = 3'b111
  } csr_op_e;
  // op == 115: I
  // Immediate (rs1 reinterpret) extract [2]

  typedef enum logic [2:0] {
    WRITEBACK_SOURCE_ALU,
    WRITEBACK_SOURCE_LSU,
    WRITEBACK_SOURCE_CONTROL,
    WRITEBACK_SOURCE_IMMEDIATE,
    WRITEBACK_SOURCE_CSR
  } writeback_source_e;

  typedef enum logic [1:0] {
    PC_SOURCE_SEQUENTIAL,
    PC_SOURCE_CONTROL,
    PC_SOURCE_CSR
  } pc_source_e;

  typedef struct packed {
    logic [4:0] rs1;
    logic [4:0] rs2;
    logic [4:0] rd;

    logic rs1_is_used;
    logic rs2_is_used;
    logic rd_write_enable;

    logic [31:0] imm;

    alu_op_e          alu_op;
    control_op_e      control_op;
    lsu_op_e          lsu_op;
    csr_op_e          csr_op;

    logic [4:0] csr_uimm;

    writeback_source_e writeback_source;
    pc_source_e        pc_source;
  } inst_semantics_t;

endpackage : rv32_inst_pkg
