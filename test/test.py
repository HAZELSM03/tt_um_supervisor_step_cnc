
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer


# =====================================================
# FUNCIONES AUXILIARES
# =====================================================

# Avanzar una cantidad determinada de ciclos.
async def ciclos(dut, cantidad):
    for _ in range(cantidad):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")


# Obtener la salida de falla: uo_out[0].
def leer_falla(dut):
    return int(dut.uo_out.value) & 1


# Modificar entradas entre flancos de reloj.
async def cambiar_entradas(dut, valor):
    await FallingEdge(dut.clk)
    dut.ui_in.value = valor


# Generar un pulso STEP en X o Y.
async def enviar_step(dut, eje):

    # STEP_X = bit 0
    # STEP_Y = bit 1
    # VIGILAR = bit 2

    await cambiar_entradas(
        dut, 0b00000100 | (1 << eje)
    )

    await ciclos(dut, 4)

    # Regresar STEP a cero.
    await cambiar_entradas(dut, 0b00000100)

    await ciclos(dut, 4)


# =====================================================
# PRUEBA DEL SUPERVISOR STEP
# =====================================================

@cocotb.test()
async def prueba_supervisor_step(dut):

    dut._log.info("INICIO: SUPERVISOR STEP CNC")

    # Configuracion inicial.
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0

    # Reloj de 10 MHz, periodo de 100 ns.
    reloj = Clock(dut.clk, 100, unit="ns")
    cocotb.start_soon(reloj.start())

    # Reinicio inicial.
    await ciclos(dut, 3)
    assert leer_falla(dut) == 0

    dut.rst_n.value = 1

    # -------------------------------------------------
    # PRUEBA 1: SUPERVISION DESHABILITADA
    # -------------------------------------------------
    dut._log.info("PRUEBA 1: Sin vigilancia")

    await ciclos(dut, 25)

    assert leer_falla(dut) == 0, \
        "Error: falla sin vigilancia"


    # -------------------------------------------------
    # PRUEBA 2: PULSOS EN EL EJE X
    # -------------------------------------------------
    dut._log.info("PRUEBA 2: Pulsos STEP X")

    await cambiar_entradas(dut, 0b00000100)

    for _ in range(3):
        await enviar_step(dut, 0)

    assert leer_falla(dut) == 0, \
        "Error: falla con actividad en X"


    # -------------------------------------------------
    # PRUEBA 3: PULSOS EN EL EJE Y
    # -------------------------------------------------
    dut._log.info("PRUEBA 3: Pulsos STEP Y")

    for _ in range(3):
        await enviar_step(dut, 1)

    assert leer_falla(dut) == 0, \
        "Error: falla con actividad en Y"


    # -------------------------------------------------
    # PRUEBA 4: PULSOS ALTERNADOS X / Y
    # -------------------------------------------------
    dut._log.info("PRUEBA 4: Pulsos alternados")

    for _ in range(3):
        await enviar_step(dut, 0)
        await enviar_step(dut, 1)

    assert leer_falla(dut) == 0, \
        "Error: falla con pulsos alternados"


    # -------------------------------------------------
    # PRUEBA 5: DESACTIVAR VIGILANCIA
    # -------------------------------------------------
    dut._log.info("PRUEBA 5: Pausa normal")

    await cambiar_entradas(dut, 0)
    await ciclos(dut, 25)

    assert leer_falla(dut) == 0, \
        "Error: falla durante pausa"


    # -------------------------------------------------
    # PRUEBA 6: AUSENCIA DE PULSOS STEP
    # -------------------------------------------------
    dut._log.info("PRUEBA 6: Ausencia de STEP")

    await cambiar_entradas(dut, 0b00000100)
    await ciclos(dut, 23)

    assert leer_falla(dut) == 1, \
        "Error: no se activo la falla"


    # -------------------------------------------------
    # PRUEBA 7: LA FALLA PERMANECE ENCLAVADA
    # -------------------------------------------------
    dut._log.info("PRUEBA 7: Regresan pulsos")

    await enviar_step(dut, 0)
    await enviar_step(dut, 1)

    assert leer_falla(dut) == 1, \
        "Error: falla no enclavada"


    # -------------------------------------------------
    # PRUEBA 8: DESACTIVAR VIGILANCIA CON FALLA
    # -------------------------------------------------
    dut._log.info("PRUEBA 8: Falla retenida")

    await cambiar_entradas(dut, 0)
    await ciclos(dut, 5)

    assert leer_falla(dut) == 1, \
        "Error: se borro la falla sin reset"


    # -------------------------------------------------
    # PRUEBA 9: REINICIO
    # -------------------------------------------------
    dut._log.info("PRUEBA 9: Reset")

    await FallingEdge(dut.clk)
    dut.rst_n.value = 0

    await ciclos(dut, 3)

    assert leer_falla(dut) == 0, \
        "Error: reset no limpio la falla"

    dut.rst_n.value = 1


    # -------------------------------------------------
    # PRUEBA 10: NUEVA SUPERVISION
    # -------------------------------------------------
    dut._log.info("PRUEBA 10: Retorno normal")

    await cambiar_entradas(dut, 0b00000100)

    for _ in range(3):
        await enviar_step(dut, 0)
        await enviar_step(dut, 1)

    assert leer_falla(dut) == 0, \
        "Error: falla despues de reset"

    # Verificar salidas no utilizadas.
    assert int(dut.uio_out.value) == 0
    assert int(dut.uio_oe.value) == 0

    dut._log.info(
        "FIN: TODAS LAS PRUEBAS SUPERADAS"
    )
