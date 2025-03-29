document.getElementById("createForm").addEventListener("submit", async function(event) {
    event.preventDefault();
    const formData = new FormData(this);

    try {
        const response = await fetch("/crear_producto", {
            method: "POST",
            body: formData,
        });

        const result = await response.json();

        if (result.success) {
            alert("Producto creado exitosamente");
            // Aquí puedes manejar la respuesta y cerrar el modal o limpiar el formulario
        } else {
            alert(`Error: ${result.error}`);
        }
    } catch (error) {
        console.error("Error al enviar el formulario:", error);
        alert("Error al enviar el formulario");
    }
});