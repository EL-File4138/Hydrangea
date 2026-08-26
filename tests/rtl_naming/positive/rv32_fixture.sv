module rv32_fixture;
  typedef enum logic { INST_FORMAT_R } inst_format_e;
  typedef struct packed { logic is_valid; } fixture_t;
endmodule : rv32_fixture
