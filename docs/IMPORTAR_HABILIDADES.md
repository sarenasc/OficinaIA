# Crear habilidades desde JSON

1. Reinicia Oficina IA para cargar la nueva ruta del servidor.
2. Abre **Habilidades → Importar JSON**.
3. Descarga la plantilla y edita las habilidades en cualquier editor de texto.
4. Carga el archivo y pulsa **Validar y ver habilidades**.
5. Abre cada habilidad de la vista previa para revisar su contenido y pulsa **Crear habilidades**.
6. En **Agentes → Herramientas y permisos**, marca la habilidad y las herramientas que necesitará; asigna también recursos y conexiones cuando corresponda.

Las habilidades son compartidas entre oficinas. No se asignan automáticamente. La importación no ejecuta instrucciones, no crea herramientas y no otorga permisos a los agentes. Las herramientas requeridas indican dependencias; el agente debe tenerlas asignadas para poder ejecutarlas.

## Formato

```json
{
  "version": 1,
  "skills": [
    {
      "name": "Revisar datos de ventas",
      "description": "Verificar archivos y sus columnas",
      "instructions": "Localiza el archivo real con filesystem.list y lee sus cabeceras con excel.read. Informa errores y no inventes datos. La lectura enviada al modelo es una muestra; no calcules totales del archivo usando solo esa muestra.",
      "required_tools": ["filesystem.list", "excel.read"],
      "examples": "Revisa las columnas de ventas.xlsx",
      "output_format": "Archivo, hojas, columnas, cantidad de filas y limitaciones"
    }
  ]
}
```

Campos: name (nombre único), instructions (procedimiento o conocimiento, obligatorio y no vacío), description, required_tools (nombres exactos o IDs de herramientas existentes y activas), examples y output_format. Los últimos cuatro campos son opcionales.

Se admiten entre 1 y 100 habilidades por lote y archivos de hasta 2 MB en el selector. No incluyas credenciales. Si una habilidad es inválida, no se guarda ninguna. No se sobrescriben habilidades existentes; los nombres duplicados se rechazan incluso si cambian mayúsculas o minúsculas.

La plantilla está en [plantilla-habilidades.json](plantilla-habilidades.json). Para agentes deportivos puedes adaptar instrucciones y ejemplos; escribir una habilidad de navegación, SQL o Python no habilita esas herramientas por sí solo.

API local autenticada: POST `/api/skills/import?preview=true` valida sin guardar. Con `preview=false` valida nuevamente y crea el lote en una transacción.
