import customtkinter as ctk        # Interfaz gráfica moderna
import subprocess                 # Para ejecutar el script ps3_syscon_uart_script.py
import serial.tools.list_ports    # Para detectar los puertos COM (USB-TTL)
import threading                  # Para leer el UART sin congelar la ventana
import os                         # Para manejar rutas de archivos y carpetas
from PIL import Image             # Para cargar logos e iconos
import re                         # El buscador de patrones (Vida y Errores)
import webbrowser                 # Para abrir enlaces (YouTube/Ayuda)
from datetime import datetime      # Para poner fecha y hora en los reportes

# =================================================================
# SECCIÓN 0: CONFIGURACIÓN DE RUTAS Y ENTORNO
# =================================================================
# Esto obliga al programa a trabajar siempre en su propia carpeta,
# así no falla al buscar el script de Syscon o las imágenes.
if os.path.dirname(os.path.abspath(__file__)):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))


class PS3SysconV60_Final(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # --- CONFIGURACIÓN DE VENTANA ---
        self.title("PS3 Syscon Tool AIO - Desarrollado por Dastier v1.0 BETA")
        self.geometry("1450x950")
        ctk.set_appearance_mode("dark")
        
        # --- 1. VARIABLES DE CONTROL DE PROCESO ---
        # Estas variables gestionan la comunicación con el script externo y el estado de la lectura
        self.proceso_actual = None      # Almacena el proceso del script ps3_syscon...
        self.esperando_eeprom = False   # Llave: TRUE activa la lectura de vida (8 bytes)
        self.conteo_visual = {}         # Diccionario dinámico: { "A0803034": Cantidad }
        self.temp_errores = []          # Lista simple de IDs detectados en la sesión actual

        # =================================================================
        # SECCIÓN 1: DICCIONARIO MAESTRO DE ERRORES (LA BIBLIA)
        # =================================================================
        # Relaciona los últimos 4 dígitos del código Syscon con su causa probable.
        self.diccionario_errores = {
            # --- SERIE 1000 (SISTEMA, ENERGÍA Y TÉRMICO) ---
            "1001": "Power CELL: Falla en el filtrado o fases del CPU. Revisar NEC/Tantalios.",
            "1002": "Power RSX: Falla en el filtrado o fases del GPU. Revisar NEC/Tantalios.",
            "1004": "AC/DC Power: La fuente no mantiene el voltaje o hay un corto masivo.",
            "1005": "Power Error: Falla general en los rieles de alimentación secundarios.",
            "1103": "Thermal Alert: Alerta del sistema por exceso de calor antes del apagado.",
            "1200": "CELL Thermal: Sobrecalentamiento crítico del CPU (>95°C). Requiere limpieza/Delid.",
            "1201": "RSX Thermal: Sobrecalentamiento crítico del GPU. Revisar montaje del disipador.",
            "1203": "CELL VR Thermal: Sobrecalentamiento en los reguladores de voltaje del CPU.",
            "1204": "SB Thermal: El Southbridge está operando fuera de rango térmico.",
            "1205": "EE/GS Thermal: Error térmico en chips de retrocompatibilidad (Modelos Fat).",
            "1214": "SB Thermal Sense: Falla en el sensor de temperatura del Southbridge.",
            "1301": "CELL PLL Unlock: El reloj del CPU no sincroniza. Problema de frecuencia.",
            "14FF": "Check Stop: El sistema se detuvo por un error catastrófico de hardware.",
            "1601": "CELL Lock Detection: El CPU se ha bloqueado durante el arranque.",
            "1701": "CELL Attention: El CPU solicita atención inmediata por fallo de bus.",
            "1802": "RSX Init: Error durante la fase de inicialización del chip de video.",
            "1900": "RTC Voltage: Voltaje de la pila de reloj (CR2032) bajo o ausente.",
            "1901": "RTC Oscillator: El oscilador de tiempo real no vibra. Revisar cristal.",
            "1902": "RTC Access: Error de comunicación con el registro de fecha y hora.",
            "1B02": "RSX Init (Alt): Fallo secundario en la secuencia de arranque del GPU.",

            # --- SERIE 2000 (ERRORES FATALES Y BUSES) ---
            "2001": "Fatal CELL: Error interno de respuesta en el procesador central.",
            "2002": "Fatal RSX: El chip de video no responde a los comandos básicos.",
            "2003": "Fatal SB: Falla de comunicación crítica con el Southbridge.",
            "2010": "Clock Subsystem: Falla en los rieles de reloj. Revisar generador de clock.",
            "2011": "CELL Clock: Error de sincronía en el bus del Cell.",
            "2012": "CELL Clock (Alt): Falla de comunicación de tiempo en el procesador.",
            "2013": "Mixed Clock: Error de reloj compartido entre CELL, RSX y SB.",
            "2020": "HDMI Error: Falla en el bus I2C del transmisor HDMI. Revisar IC controlador.",
            "2022": "DVE Error: Falla en el codificador de video analógico (Componentes/AV).",
            "2024": "HDMI/AV Check: El sistema no detecta salida de video válida.",
            "2030": "CELL Thermal Sensor: Sensor CPU no responde o lectura errónea.",
            "2031": "RSX Thermal Sensor: El sensor interno del GPU no responde.",
            "2033": "SB Thermal Sensor: Falla en el reporte térmico del Southbridge.",
            "2040": "5V_MISC: Error en línea 5V secundaria. Revisar reguladores.",
            "2044": "Short Circuit (SuperSlim): Corto en 5V relacionado a módulo BT/Wi-Fi.",
            "2101": "CELL I/O Error: Error de entrada/salida en el bus del procesador.",
            "2102": "RSX I/O Error: Error de entrada/salida en el bus del chip de video.",
            "2103": "SB I/O Error: Error de entrada/salida en el Southbridge.",
            "2110": "Clock Subsystem (IO): Error de sincronización de bus de datos.",
            "2111": "CELL Clock (IO): Falla de comunicación por reloj en el Cell.",
            "2112": "CELL Clock (IO Alt): Error persistente de frecuencia en CPU.",
            "2113": "Mixed Clock (IO): Error de tiempo en comunicación triple.",
            "2120": "HDMI I/O: El controlador HDMI (Sil9132) no responde por bus I2C.",
            "2122": "DVE I/O: Error de datos en el controlador de video analógico.",
            "2124": "HDMI/AV I/O: Error de handshake en la salida de video.",
            "2130": "CELL Thermal (IO): El registro térmico del CPU está bloqueado.",
            "2131": "RSX Thermal (IO): El registro térmico del GPU está bloqueado.",
            "2133": "SB Thermal (IO): Error de acceso al sensor del Southbridge.",
            "2203": "SB Communication: El Southbridge perdió el enlace con el Syscon.",
            "2310": "System Bus Error: Error general en los buses de datos.",

            # --- SERIE 3000 (ARRANQUE FATAL) ---
            "3000": "Fatal Boot: Error de inicio paso 0. Hardware no responde.",
            "3001": "Fatal Boot (Step 1): Falla temprana en cadena de encendido.",
            "3002": "Fatal Boot (Step 2): Parada antes de inicializar CPU.",
            "3003": "CELL Core Power: Falla crítica de energía en núcleo CPU (VDDC).",
            "3004": "RSX Core Power: Falla crítica de energía en núcleo GPU (VDDR).",
            "3005": "VRAM/XDR Power: Error en voltajes de memorias RAM.",
            "3010": "CELL Fatal: El procesador central no inició. Revisar VCore.",
            "3011": "RSX Fatal: El procesador de video no inició. Posible corto.",
            "3012": "SB Fatal: El Southbridge no responde al arranque.",
            "3013": "Mixed Fatal: Error de sincronía múltiple (Check HDMI).",
            "3020": "I2C Fatal: Un integrado bloquea la línea de datos principal.",
            "3030": "BE-RSX Link: Error de conexión entre CPU y GPU (FlexIO).",
            "3031": "BE-SB Link: Error de conexión entre CPU y Southbridge.",
            "3032": "RSX-SB Link: Error de conexión entre GPU y Southbridge.",
            "3033": "Internal Bus Fatal: Error en anillo de comunicación interno.",
            "3034": "RSX GLUE Error: Falla enlace video. Candidato a Reballing.",
            "3035": "BE GLUE Error: Falla de enlace en el procesador central.",
            "3036": "SB GLUE Error: Falla de enlace en el Southbridge.",
            "3037": "DRAM Glue: Error de comunicación con la RAM del sistema.",
            "3038": "VRAM Glue: Error de comunicación con la memoria de video.",
            "3039": "System Glue Error: Error lógico en interconexión principal.",
            "3040": "COK Power Error: Falla reguladores en placas retro (COK).",
            "3041": "Unknown Hardware: Componente no identificado o dañado.",

            # --- SERIE 4000 (DATOS Y RAM) ---
            "4001": "BE XDR Data: Error de datos en bus de memoria XDR.",
            "4002": "BE XDR Address: Error direccionamiento en RAM del Cell.",
            "4003": "BE XDR Control: Error en señales de control de memoria.",
            "4011": "BE XDR Fatal: Fallo total de comunicación con banco XDR.",
            "4101": "FlexIO Data: Error de datos en enlace Cell <-> RSX.",
            "4102": "FlexIO Address: Error dirección en enlace Cell <-> RSX.",
            "4103": "FlexIO Control: Error protocolo en bus FlexIO.",
            "4111": "FlexIO Fatal: Desconexión crítica entre procesadores.",
            "4201": "SB Data: Error de datos en bus del Southbridge.",
            "4202": "SB Address: Error direccionamiento hacia Southbridge.",
            "4203": "SB Control: Error control en periféricos (SATA/USB).",
            "4211": "SB Fatal: Fallo masivo comunicación con Southbridge.",
            "4212": "SB Config: Error configuración en registros del SB.",
            "4221": "SB PLL: Error sincronía en reloj del Southbridge.",
            "4222": "SB Reset: El Southbridge no sale del estado de reset.",
            "4231": "SB Interface: Error en interfaz física del Southbridge.",
            "4261": "SB Internal: Error lógico interno en chip Bridge.",
            "4301": "RSX VRAM Data: Error de datos en memorias de video GDDR3.",
            "4302": "RSX VRAM Address: Error dirección en memorias de video.",
            "4303": "RSX VRAM Control: Error de control en la VRAM.",
            "4311": "RSX VRAM Fatal: Fallo crítico acceso memoria de video.",
            "4312": "RSX VRAM Config: Error parámetros controlador de video.",
            "4321": "RSX VRAM PLL: Falla de reloj en memorias del GPU.",
            "4322": "RSX VRAM Reset: Error reinicio en bancos de video.",
            "4332": "RSX VRAM Interface: Falla física en bus de la VRAM.",
            "4341": "RSX VRAM Training: Error calibración encendido VRAM.",
            "4401": "Memory Read: Error de lectura persistente en RAM.",
            "4402": "Memory Write: Error de escritura persistente en RAM.",
            "4403": "Memory Timeout: El bus de memoria dejó de responder.",
            "4411": "Data Corruption: Datos corruptos detectados por Syscon.",
            "4412": "ECC Error: Error corrección de datos en bus memoria.",
            "4421": "Bus Conflict: Conflicto direcciones en bus de datos.",
            "4422": "Bus Parity: Error paridad en transmisión de datos.",
            "4432": "Interface Conflict: Conflicto entre interfaces memoria.",
            "4441": "Memory Init: Error fatal inicializando la RAM.",
            "5FFF": "System Checkstop: Parada por inconsistencia de datos.",

            # --- SERIE 9000 Y VARIOS ---
            "9010": "System Error: Error lógico en kernel del Syscon.",
            "9012": "I2C Timeout: Bus colgado esperando sensor.",
            "9020": "UART Error: Falla comunicación interna puerto diagnóstico.",
            "9201": "Flash Read: Error lectura NAND/NOR. Firmware corrupto.",
            "9202": "Flash Write: Error al escribir en Flash (Update fallido).",
            "09203": "Flash Auth: Error autenticación. Flash != Cell.",
            "9210": "SPI Flash Error: Bus SPI hacia Flash fallando.",
            "8010": "PATA/SATA Error: SB no detecta el Disco Rígido.",
            "8011": "BD-ROM Error: Falla comunicación con lectora.",
            "8020": "USB Overcurrent: Corto detectado en puerto USB.",
            "FFFF": "Panic Stop: Error grave que bloqueó el hardware."
        }

        

# ==========================================================
        # SECCIÓN 2: ESTRUCTURA DE LA INTERFAZ (GRID & LAYOUT)
        # ==========================================================
        # Configuramos pesos para que la consola central (Col 1) sea la que más crezca
        self.grid_columnconfigure(0, weight=0) # Menú lateral (Fijo)
        self.grid_columnconfigure(1, weight=3) # Consola de comandos (Expandible)
        self.grid_columnconfigure(2, weight=0) # Panel de datos (Fijo)
        self.grid_rowconfigure(0, weight=1)

        # ----------------------------------------------------------
        # 2.1 SIDEBAR IZQUIERDO: CONTROLES Y SELECCIÓN
        # ----------------------------------------------------------
        self.sidebar = ctk.CTkScrollableFrame(self, width=320, corner_radius=0, fg_color="#161d24")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Cabecera del Menú
        ctk.CTkLabel(self.sidebar, text="-PS3 SYSCON TOOL AIO-", 
                     font=("Segoe UI", 22, "bold"), text_color="#27ae60").pack(pady=(25, 5))
        ctk.CTkLabel(self.sidebar, text="Versión Beta Publica - Dastier_77", 
                     font=("Segoe UI", 12), text_color="#57606f").pack(pady=(0, 20))

        # --- GRUPO: CONEXIÓN SERIAL ---
        ctk.CTkLabel(self.sidebar, text="PUERTO SERIAL:", font=("Arial", 11, "bold"), text_color="gray").pack(pady=(10, 0))
        self.combo_puertos = ctk.CTkComboBox(self.sidebar, width=220, height=35, font=("Arial", 14))
        self.combo_puertos.pack(pady=5)
        
        self.actualizar_puertos() # Carga inicial de puertos COM detectados
        
        ctk.CTkButton(self.sidebar, text="RE-ESCANEAR", fg_color="#34495e", hover_color="#2c3e50",
                      height=35, font=("Arial", 12, "bold"),
                      command=self.actualizar_puertos).pack(pady=5)

        # --- GRUPO: SELECCIÓN DE HARDWARE ---
        self.crear_seccion("--- MODELO DE PLACA ---")
        self.db_chips = {
            "COK-001 (Fat)": "CXR",
            "COK-002 (Fat)": "CXR",
            "SEM-001 (Fat)": "CXR",
            "DIA-001 (Fat)": "CXR",
            "DIA-002 (Fat)": "CXR",
            "VER-001 (Fat)": "CXR",
            "DYN-001 (Slim 20xxA/B)": "CXR",
            "SUR-001 (Slim 21xxA/B)": "SW",
            "JTP-001 (Slim 25xxA/B)": "SW",
            "JSD-001 (Slim 25xxA/B)": "SW",
            "KTE-001 (Slim 30xxA/B)": "SW",
            "MSX-001 (S.Slim 40xxA/B/C)": "SW",
            "MPX-001 (S.Slim 40xxA/B/C)": "SW",
            "NPX-001 (S.Slim 42xxA/B/C)": "SW",
            "PPX-001 (S.Slim 42xxA/B/C)": "SW",
            "PQX-001 (S.Slim 42xxA/B/C)": "SW",
            "RAX-001 (S.Slim 42xxA/B/C)": "SW",
            "RTX-001 (S.Slim 43xxA/B/C)": "SW",
            "REX-001 (S.Slim 43xxA/B/C)": "SW"
        }
        self.tipo_chip = ctk.StringVar(value="CXR") 
        self.combo_placas = ctk.CTkComboBox(self.sidebar, values=list(self.db_chips.keys()), 
                                            command=self.actualizar_chip_por_placa, width=260)
        self.combo_placas.pack(pady=10, padx=20)
        self.combo_placas.set("Seleccione Placa...")

        self.lbl_chip_info = ctk.CTkLabel(self.sidebar, text="Chip: ---", font=("Arial", 11, "bold"), text_color="#aaa")
        self.lbl_chip_info.pack(pady=(0, 5))

        # ==========================================================
        # RECONSTRUCCIÓN DEL MENÚ LATERAL (TODOS LOS BOTONES)
        # ==========================================================
        
        # --- 1. CONEXIÓN Y AUTH ---
        self.crear_seccion("--- CONEXIÓN UART ---")
        self.crear_boton("1. CONECTAR UART", "#27ae60", self.iniciar_conexion)
        self.crear_boton("2. ENVIAR AUTH ", "#2980b9", lambda: self.inyectar_comando("auth"))
        self.crear_boton("3. DESCONECTAR ", "#d35400", self.detener_conexion)

        # --- 2. DIAGNÓSTICO BÁSICO (LOS INFALIBLES) ---
        self.crear_seccion("--- DIAGNÓSTICO ---")
        self.crear_boton("VER ERRORES (errlog)", "#1a5276", self.obtener_errores_limpios)
        self.crear_boton("VIDA DE PLACA (r 800)", "#8e44ad", self.obtener_uso_limpio)
        self.crear_boton("BORRAR LOG (clear)", "#c0392b", self.borrar_log_syscon)

        # --- 3. HARDWARE Y VOLTAJES (BRINGUP) ---
        self.crear_seccion("--- HARDWARE & ENERGY ---")
        self.crear_boton("TEST VOLTAJES (bringup)", "#d35400", self.check_voltajes_riel)
        self.crear_boton("VER ESTADO (lasterr)", "#f39c12", lambda: self.inyectar_comando("lasterrlog"))

        # --- 4. AVANZADO (PARA EL EXPERTO) ---
        self.crear_seccion("--- ANÁLISIS AVANZADO ---")
        self.crear_boton("PASO DE FALLO (extstat)", "#2980b9", self.obtener_extstat)
        self.crear_boton("VERIFICAR CHIP (cks)", "#2c3e50", self.obtener_cks)
        self.crear_boton("INFO SISTEMA (ver)", "#34495e", lambda: self.inyectar_comando("ver"))

        # --- 5. RECURSOS EXTERNOS ---
        self.crear_seccion("--- RECURSOS & REPORTES ---")
        self.crear_boton("GENERAR REPORTE .TXT", "#1abc9c", self.generar_reporte_tecnico)
        self.crear_boton("FOTOS SOLDADURAS", "#d87093", self.abrir_carpeta_soldaduras)
        self.crear_boton("WIKI DE ERRORES", "#34495e", 
                         lambda: webbrowser.open("https://www.psdevwiki.com/ps3/Syscon_Error_Codes"))

        # --- 6. CONTROL FINAL ---
        self.crear_seccion("--- PANEL DE CONTROL ---")
        ctk.CTkButton(self.sidebar, text="LIMPIAR TODO", fg_color="#57606f", 
                      height=40, command=self.limpiar_todo).pack(pady=5, padx=25)
        ctk.CTkButton(self.sidebar, text="SALIR DE APP ❌", fg_color="#e74c3c", 
                      height=45, font=("Arial", 12, "bold"), command=self.quit).pack(pady=15)
        # ----------------------------------------------------------
        # 2.2 CONSOLA CENTRAL (VIEWPORT)
        # ----------------------------------------------------------
        self.txt_display = ctk.CTkTextbox(
            self, 
            font=("Consolas", 16, "bold"), 
            fg_color="#000000", # Fondo negro puro para visibilidad en video
            text_color="#ffffff",
            padx=20, pady=20, corner_radius=15, border_width=2, border_color="#1e272e"
        )
        self.txt_display.grid(row=0, column=1, sticky="nsew", padx=10, pady=15)

        # Configuración de resaltado por colores
        self.txt_display.tag_config("sys", foreground="#2ecc71")   # Sistema: Verde
        self.txt_display.tag_config("error", foreground="#ff4757") # Fallos: Rojo
        self.txt_display.tag_config("uart", foreground="#3498db")  # Datos: Azul

        # ----------------------------------------------------------
        # 2.3 PANEL DERECHO: SÍNTESIS Y DIAGNÓSTICO RÁPIDO
        # ----------------------------------------------------------
        self.panel_derecho_container = ctk.CTkFrame(self, width=380, fg_color="transparent")
        self.panel_derecho_container.grid(row=0, column=2, sticky="nsew", padx=15, pady=15)

        # CARD: Estadística de Uso (Contadores de la consola)
        self.card_sintesis = ctk.CTkFrame(self.panel_derecho_container, fg_color="#161d24", corner_radius=15, border_width=1, border_color="#34495e")
        self.card_sintesis.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(self.card_sintesis, text="-/ SÍNTESIS DE PLACA /-", font=("Segoe UI", 16, "bold"), text_color="#f1c40f").pack(pady=(12, 8))
        
        self.lbl_boots = self.crear_label_info_en_card(self.card_sintesis, "Arranques Totales:", "---", color="#2ecc71")
        self.lbl_offs = self.crear_label_info_en_card(self.card_sintesis, "Apagados Normales:", "---", color="#3498db")
        self.lbl_fallas = self.crear_label_info_en_card(self.card_sintesis, "Apagados con FALLO:", "---", color="#e74c3c")
        self.lbl_uso = self.crear_label_info_en_card(self.card_sintesis, "Tiempo Total de Uso:", "---")

        # CARD: Resumen de Errores (Diagnóstico sugerido)
        self.card_tecnico = ctk.CTkFrame(self.panel_derecho_container, fg_color="#161d24", corner_radius=15, border_width=1, border_color="#34495e")
        self.card_tecnico.pack(fill="x", pady=10)
        ctk.CTkLabel(self.card_tecnico, text="-/ ESTADO TÉCNICO /-", font=("Segoe UI", 13, "bold"), text_color="#3498db").pack(pady=(12, 5))
        
        self.txt_errores_resumen = ctk.CTkTextbox(
            self.card_tecnico, height=200, width=320, 
            font=("Consolas", 12, "bold"), fg_color="#0b0f13",
            border_width=1, border_color="#2c3e50"
        )
        self.txt_errores_resumen.pack(padx=15, pady=(5, 15))

        # CARD: Branding
        self.card_autor = ctk.CTkFrame(self.panel_derecho_container, fg_color="#161d24", corner_radius=15, border_width=2, border_color="#27ae60")
        self.card_autor.pack(fill="x", pady=10)
        ctk.CTkLabel(self.card_autor, text="DASTIER_77", font=("Segoe UI", 18, "bold"), text_color="#27ae60").pack(pady=(12, 0))
        
        ctk.CTkButton(self.card_autor, text="CANAL YOUTUBE", command=lambda: webbrowser.open("https://www.youtube.com/@Dastier_77")).pack(pady=15, padx=25, fill="x")
        
    # ==========================================================
    # 4. SECCIÓN: MÉTODOS DE SOPORTE UI (INTERFAZ)
    # ==========================================================

    def actualizar_chip_por_placa(self, seleccion):
        """ Cambia el modo (CXR/SW) según la placa elegida y limpia el resumen """
        modo = self.db_chips.get(seleccion)
        self.tipo_chip.set(modo)
        color = "#2ecc71" if modo == "CXR" else "#3498db"
        self.lbl_chip_info.configure(text=f"MODO ACTIVO: {modo}", text_color=color)
        
        # Reset del cuadro de resumen para nueva sesión
        self.txt_errores_resumen.configure(state="normal")
        self.txt_errores_resumen.delete("1.0", "end")
        self.txt_errores_resumen.insert("1.0", f"📍 PLACA: {seleccion}\n" + "-"*34 + "\n")
        self.txt_errores_resumen.configure(state="disabled")

    def crear_label_info_en_card(self, parent, titulo, valor, color="#ffffff"):
        """ Crea los pares de etiquetas (Título: Valor) en los paneles derechos """
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(frame, text=titulo, font=("Arial", 11), text_color="#57606f").pack(side="left")
        lbl = ctk.CTkLabel(frame, text=valor, font=("Consolas", 14, "bold"), text_color=color)
        lbl.pack(side="right")
        return lbl

    def crear_seccion(self, texto):
        """ Separadores de texto en el sidebar """
        ctk.CTkLabel(self.sidebar, text=texto, font=("Arial", 10, "bold"), text_color="#666").pack(pady=(12, 2))

    def crear_boton(self, texto, color, comando):
        """ Generador de botones estándar del menú lateral """
        btn = ctk.CTkButton(self.sidebar, text=texto, fg_color=color, height=42, 
                            font=("Arial", 12, "bold"), command=comando)
        btn.pack(pady=4, padx=25)
        return btn

    def actualizar_puertos(self):
        """ Escanea los puertos COM disponibles (USB-TTL) """
        puertos = [p.device for p in serial.tools.list_ports.comports()]
        self.combo_puertos.configure(values=puertos if puertos else ["No detectado"])
        if puertos: self.combo_puertos.set(puertos[0])

    # ==========================================================
    # 5. SECCIÓN: LÓGICA DE COMUNICACIÓN Y MOTOR DE DATOS
    # ==========================================================

    def inyectar_comando(self, cmd):
        """ Envía un comando de texto directamente al Syscon """
        if self.proceso_actual and self.proceso_actual.poll() is None:
            try:
                comando_final = cmd.strip() + "\n"
                self.proceso_actual.stdin.write(comando_final)
                self.proceso_actual.stdin.flush()
                self.actualizar_interfaz_hilo(f"> {cmd.strip()}")
            except Exception as e:
                print(f"Error inyectando: {e}")
        else:
            self.actualizar_interfaz_hilo("[SISTEMA] ❌ Error: Conecte el UART primero.")

    def iniciar_conexion(self): 
        """ Lanza el proceso de conexión en un hilo separado para no colgar la App """
        threading.Thread(target=self.ejecutar_proceso, daemon=True).start()

    def ejecutar_proceso(self):
        """ Configura y lanza el script de Python externo (ps3_syscon_uart_script.py) """
        puerto = self.combo_puertos.get()
        modo = self.tipo_chip.get()
        
        # Búsqueda automática del script en la carpeta del programa
        script_path = None
        for root, _, files in os.walk("."):
            if "ps3_syscon_uart_script.py" in files: 
                script_path = os.path.normpath(os.path.join(root, "ps3_syscon_uart_script.py"))
                break
        
        if not script_path: 
            self.actualizar_interfaz_hilo("❌ ERROR: No se encontró ps3_syscon_uart_script.py")
            return

        import sys
        comando = [sys.executable, "-u", script_path, puerto, modo]
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

        try:
            self.proceso_actual = subprocess.Popen(
                comando, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, text=True, shell=False, bufsize=1, creationflags=flags
            )
            self.actualizar_interfaz_hilo(f"[SISTEMA] 🔌 Conectando a {puerto} ({modo})...")
            
            # Hilo de escucha permanente
            threading.Thread(target=self.leer_salida_hilo, daemon=True).start()
        except Exception as e:
            self.actualizar_interfaz_hilo(f"❌ Error al iniciar: {e}")

    def leer_salida_hilo(self):
        """ Lee línea por línea lo que responde el Syscon """
        auth_intentado = False
        try:
            for linea in iter(self.proceso_actual.stdout.readline, ''):
                l_limpia = linea.strip()
                if not l_limpia: continue

                # Auto-Auth: Si vemos el prompt '>', enviamos 'auth' automáticamente
                if ">" in l_limpia and not auth_intentado:
                    self.after(600, lambda: self.inyectar_comando("auth"))
                    auth_intentado = True

                # Enviamos el texto a la pantalla principal
                self.after(0, lambda l=l_limpia: self.actualizar_interfaz_hilo(l))
        except:
            self.after(0, lambda: self.actualizar_interfaz_hilo("[SISTEMA] 🔌 Conexión finalizada."))
        finally:
            self.proceso_actual = None

    def actualizar_interfaz_hilo(self, linea):
        """ Aplica colores a la consola y dispara el análisis técnico """
        l_up = linea.upper()
        tag = None
        
        if any(x in l_up for x in ["ERROR", "FAIL", "❌", "DENIED"]): tag = "error"
        elif "[SISTEMA]" in l_up: tag = "sys" 
        elif ">" in linea: tag = "uart"

        self.txt_display.configure(state="normal") 
        self.txt_display.insert("end", linea + "\n", tag)
        
        # Solo procesamos datos reales (filtramos avisos del sistema)
        if "[SISTEMA]" not in l_up: 
            self.procesar_salida(linea) 
            
        self.txt_display.see("end")
        self.txt_display.configure(state="disabled")

    # ----------------------------------------------------------
    # MOTOR TÉCNICO V60.1 (EL CEREBRO DE DASTIER)
    # ----------------------------------------------------------
    def procesar_salida(self, linea):
        """ Analiza patrones A0 (Errores) y R 800 8 (Vida de la placa) """
        linea_up = linea.upper().strip()
        linea_pura = linea_up.replace("#", "").replace(">", "").strip()

        # --- BUSCADOR DE ERRORES (A0XXXXXX) ---
        error_match = re.search(r'A[0-9A-F]{7}', linea_pura)
        if error_match:
            full_code = error_match.group()
            id_real = full_code[-4:] # Tomamos los últimos 4 dígitos
            
            if not hasattr(self, 'conteo_visual'): self.conteo_visual = {}
            
            # Contabilizamos el error
            if full_code not in self.conteo_visual:
                desc = self.diccionario_errores.get(id_real, f"Falla {id_real}")
                self.conteo_visual[full_code] = {"desc": desc, "paso": full_code[2:4], "cant": 1}
            else:
                self.conteo_visual[full_code]["cant"] += 1

            # Redibujamos el panel de resumen derecho
            self.actualizar_panel_resumen()
            return 

        # --- BUSCADOR DE TIEMPO DE VIDA (r 800 8) ---
        if self.esperando_eeprom and "#" in linea_up:
            if "+" in linea_up or "---" in linea_up: return
            
            datos = re.findall(r'[0-9A-F]{2}', linea_up)
            if len(datos) == 8:
                try:
                    v_arr = int(f"{datos[0]}{datos[1]}", 16)
                    v_off = int(f"{datos[2]}{datos[3]}", 16)
                    v_seg = int(f"{datos[4]}{datos[5]}{datos[6]}{datos[7]}", 16)
                    
                    # Actualización de Labels en tiempo real
                    self.lbl_boots.configure(text=str(v_arr), text_color="#2ecc71")
                    self.lbl_offs.configure(text=str(v_off), text_color="#3498db")
                    self.lbl_fallas.configure(text=str(max(0, v_arr - v_off)), text_color="#e74c3c")
                    
                    dd = v_seg // 86400
                    hh = (v_seg % 86400) // 3600
                    mm = (v_seg % 3600) // 60  # <-- Agregamos el cálculo de minutos
                    
                    # Actualizamos el Label incluyendo los minutos
                    self.lbl_uso.configure(text=f"{dd}d {hh}h {mm}m", text_color="#f1c40f")
                    
                    self.esperando_eeprom = False
                except: pass

    def actualizar_panel_resumen(self):
        """ Función interna para refrescar el cuadro de texto de la derecha """
        self.txt_errores_resumen.configure(state="normal")
        self.txt_errores_resumen.delete("1.0", "end")
        self.txt_errores_resumen.insert("end", f"📍 PLACA: {self.combo_placas.get()}\n" + "-"*34 + "\n")
        
        for code, info in self.conteo_visual.items():
            x_veces = f" [x{info['cant']}]" if info['cant'] > 1 else ""
            self.txt_errores_resumen.insert("end", f"❌ {code}{x_veces}\n")
            self.txt_errores_resumen.insert("end", f"📍 Paso {info['paso']}: {info['desc']}\n" + "─"*34 + "\n")
        
        self.txt_errores_resumen.configure(state="disabled")

   # ==========================================================
    # 7. SECCIÓN: MÉTODOS DE BOTONES (ACCIONES TÉCNICAS)
    # ==========================================================

    # --- UTILIDADES DE DIAGNÓSTICO ---
    def obtener_uso_limpio(self): 
        """ Dispara la lectura de la EEPROM para calcular vida útil """
        self.actualizar_interfaz_hilo("[SISTEMA] 🔍 Obteniendo estado de vida de la placa...")
        
        # Feedback visual de espera
        self.lbl_uso.configure(text="Calculando...", text_color="gray")
        self.lbl_boots.configure(text="⌛", text_color="gray")

        # Activamos bandera para que el procesador intercepte la respuesta hexadecimal
        self.esperando_eeprom = True
        self.inyectar_comando("r 800 8")

    def obtener_errores_limpios(self): 
        """ Solicita el log de errores al Syscon """
        self.esperando_eeprom = False
        self.inyectar_comando("errlog")

    def borrar_log_syscon(self):
        """ Limpia el historial interno del Syscon (Cuidado: Acción irreversible) """
        self.inyectar_comando("errlog clear")

    # --- COMANDOS DE HARDWARE & AVANZADO ---
    def check_voltajes_riel(self):
        """ Ejecuta la secuencia de encendido para testear voltajes """
        self.actualizar_interfaz_hilo("[SISTEMA] ⚡ Iniciando secuencia Bringup...")
        self.inyectar_comando("bringup")

    def obtener_extstat(self):
        """ Muestra el estado extendido (Paso de falla exacto) """
        self.inyectar_comando("extstat")

    def obtener_cks(self):
        """ Verifica el Checksum del Syscon para descartar corrupción de datos """
        self.inyectar_comando("cks")

    # --- GESTIÓN DE RECURSOS ---
    def abrir_carpeta_soldaduras(self):
        """ Acceso rápido a tus diagramas de soldadura locales """
        ruta_base = os.path.dirname(os.path.abspath(__file__))
        ruta_carpeta = os.path.join(ruta_base, "imagen soldaduras")
        
        if os.path.exists(ruta_carpeta):
            os.startfile(ruta_carpeta)
        else:
            self.actualizar_interfaz_hilo(f"❌ ERROR: Carpeta no encontrada en:\n{ruta_carpeta}")

    def detener_conexion(self):
        """ Mata el proceso de Python que controla el UART de forma segura """
        if self.proceso_actual:
            self.actualizar_interfaz_hilo("[SISTEMA] 🛑 Cerrando conexión UART...")
            self.proceso_actual.terminate() 
            self.proceso_actual = None
            self.actualizar_interfaz_hilo("[SISTEMA] 🔌 UART DESCONECTADO.")
        else:
            self.actualizar_interfaz_hilo("[SISTEMA] ℹ️ No hay conexiones activas.")

    def generar_reporte_tecnico(self):
        """ Exporta la sesión actual a un archivo .txt para el cliente """
        dialogo = ctk.CTkInputDialog(text="Nombre del reporte (ej: Cliente_PS3_Fat):", title="Guardar Reporte")
        nombre = dialogo.get_input()
        if nombre:
            try:
                with open(f"Reporte_{nombre}.txt", "w", encoding="utf-8") as f:
                    f.write(f"REPORTE TÉCNICO - DASTIER_77\n")
                    f.write(f"PLACA: {self.combo_placas.get()}\n")
                    f.write("="*40 + "\n")
                    f.write(self.txt_display.get("1.0", "end"))
                self.actualizar_interfaz_hilo(f"[SISTEMA] ✅ Reporte 'Reporte_{nombre}.txt' guardado.")
            except Exception as e:
                self.actualizar_interfaz_hilo(f"❌ Error al guardar: {e}")

    def limpiar_todo(self):
        """ Reset total de la interfaz para una nueva reparación """
        self.conteo_visual = {} # Limpiar memoria de errores detectados
        
        # Limpiar consola central
        self.txt_display.configure(state="normal")
        self.txt_display.delete("1.0", "end")
        self.txt_display.configure(state="disabled")

        # Limpiar panel derecho
        self.txt_errores_resumen.configure(state="normal")
        self.txt_errores_resumen.delete("1.0", "end")
        placa = self.combo_placas.get()
        if "Seleccione" not in placa:
            self.txt_errores_resumen.insert("1.0", f"📍 PLACA: {placa}\n" + "-"*34 + "\n")
        self.txt_errores_resumen.configure(state="disabled")

        # Reset de etiquetas numéricas
        for lbl in [self.lbl_boots, self.lbl_offs, self.lbl_fallas, self.lbl_uso]:
            lbl.configure(text="---", text_color="gray")
            
        self.actualizar_interfaz_hilo("[SISTEMA] 🧹 Interfaz limpia para nuevo diagnóstico.")

    def crear_label_info_en_card(self, master, titulo, valor_inicial, color="#2ecc71"):
        """ Helper para organizar la información en las tarjetas del panel derecho """
        frame = ctk.CTkFrame(master, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        
        ctk.CTkLabel(frame, text=titulo, font=("Segoe UI", 11), text_color="#57606f").pack(side="left")
        lbl = ctk.CTkLabel(frame, text=valor_inicial, font=("Consolas", 14, "bold"), text_color=color)
        lbl.pack(side="right")
        return lbl

# ==========================================================
# LANZAMIENTO DE LA APLICACIÓN
# ==========================================================
if __name__ == "__main__":
    try:
        app = PS3SysconV60_Final()
        app.mainloop()
    except Exception as e:
        print(f"Error fatal al iniciar la App: {e}")