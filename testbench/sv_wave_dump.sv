module sv_wave_dump;
    string wave_file;

    initial begin
        if (!$value$plusargs("WAVE_FILE=%s", wave_file)) begin
            wave_file = "simulation_wave/sv.vcd";
        end
        $dumpfile(wave_file);
        $dumpvars(0);
    end
endmodule
