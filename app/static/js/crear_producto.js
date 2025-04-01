document.getElementById("createForm").addEventListener("submit", async function(event) {
    event.preventDefault(); // Evita el comportamiento predeterminado del formulario

    // Crear un objeto FormData para capturar los datos del formulario
    const formData = new FormData(this);

    // Depuración: Verificar los datos que se están enviando
    console.log("Datos enviados al backend:");

    try {
        // Enviar los datos al backend
        const response = await fetch("/crear_producto", {
            method: "POST",
            body: formData, // Enviar FormData directamente
        });

        // Procesar la respuesta del servidor
        const result = await response.json();

        if (result.success) {
            alert("Producto creado correctamente");
            closeCreateModal(); // Cierra el modal de creación
            loadProducts(); // Recarga la lista de productos
        } else {
            alert("Error al crear el producto: " + (result.error || ''));
        }
    } catch (error) {
        console.error("Error al enviar el formulario:", error);
        alert("Error al enviar el formulario");
    }
});