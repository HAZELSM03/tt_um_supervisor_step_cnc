
`default_nettype none

// ======================================================
// MODULO PRINCIPAL PARA TINY TAPEOUT GF180
// ======================================================

module tt_um_supervisor_step_cnc (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

    // Adaptacion del reset:
    // Tiny Tapeout: activo en 0
    // Supervisor STEP: activo en 1
    wire reset = ~rst_n;

    wire falla;

    // INSTANCIA DEL SUPERVISOR ORIGINAL
    supervisor_step #(
        .TIMEOUT(20)
    ) guardian (
        .clk(clk),
        .reset(reset),
        .step_x(ui_in[0]),
        .step_y(ui_in[1]),
        .vigilar_movimiento(ui_in[2]),
        .falla(falla)
    );

    // Salida de falla en uo_out[0]
    assign uo_out = {7'b0000000, falla};

    // Pines bidireccionales no utilizados
    assign uio_out = 8'b00000000;
    assign uio_oe  = 8'b00000000;

    // Evitar advertencias por entradas sin utilizar
    wire _unused = &{ena, ui_in[7:3], uio_in, 1'b0};

endmodule


// ======================================================
// SUPERVISOR STEP ORIGINAL
// ======================================================

module supervisor_step #(
    parameter integer TIMEOUT = 20
)(
    input  wire clk,
    input  wire reset,
    input  wire step_x,
    input  wire step_y,
    input  wire vigilar_movimiento,
    output reg  falla
);

    // BLOQUE 1. REGISTROS INTERNOS
    reg [4:0] contador;

    reg x_meta, x_sync, x_anterior;
    reg y_meta, y_sync, y_anterior;

    // BLOQUE 2. SINCRONIZACION
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            x_meta     <= 1'b0;
            x_sync     <= 1'b0;
            x_anterior <= 1'b0;

            y_meta     <= 1'b0;
            y_sync     <= 1'b0;
            y_anterior <= 1'b0;
        end
        else begin
            x_meta     <= step_x;
            x_sync     <= x_meta;
            x_anterior <= x_sync;

            y_meta     <= step_y;
            y_sync     <= y_meta;
            y_anterior <= y_sync;
        end
    end

    // BLOQUE 3. DETECCION DE FLANCOS
    wire pulso_x = x_sync && !x_anterior;
    wire pulso_y = y_sync && !y_anterior;

    wire pulso_step = pulso_x || pulso_y;

    // BLOQUE 4. TEMPORIZADOR Y FALLA
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            contador <= 5'd0;
            falla    <= 1'b0;
        end
        else if (falla) begin
            falla <= 1'b1;
        end
        else if (!vigilar_movimiento) begin
            contador <= 5'd0;
        end
        else if (pulso_step) begin
            contador <= 5'd0;
        end
        else if (contador >= TIMEOUT - 1) begin
            falla <= 1'b1;
        end
        else begin
            contador <= contador + 1'b1;
        end
    end

endmodule

`default_nettype wire
