# Constructor de oficinas

Selecciona una oficina en el filtro superior y entra en **Agentes → Construir oficina**.
El constructor abre el plano 2D y conserva los escritorios existentes.

1. Usa **+ Sala** para añadir una sala rectangular. Escribe su nombre, ancho y fondo,
   y elige en qué lado estará su puerta.
2. Usa **+ División** para añadir una pared horizontal o vertical. Puedes dejar un
   paso central o crear una pared continua.
3. Arrastra salas, divisiones y escritorios en el plano. También puedes seleccionarlos
   con Tab y moverlos con las flechas. Los campos X/Y permiten ajustar la posición.
4. Pulsa **Guardar distribución**. **Cancelar** descarta los cambios pendientes.
5. Abre **Oficina 3D** para ver las salas y paredes construidas.

Las medidas usan unidades del plano, con ajuste a una cuadrícula de 20 unidades.
Cada puerta deja un paso de 100 unidades. Coloca los escritorios dejando espacio
para las sillas y el acceso a las puertas; evita superponer paredes con escritorios
o bloquear una puerta con otra división. Los recorridos buscan pasos libres y se
omiten si no existe un camino accesible.

El plano se guarda por oficina, también se conserva al duplicarla y no requiere
migrar la base de datos. Se admiten hasta 40 salas y 80 divisiones. Si otra ventana
guarda un plano mientras editas, recarga antes de volver a guardar.
