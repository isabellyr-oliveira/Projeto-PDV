document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("searchInput");
    const categorySelect = document.getElementById("categorySelect");
    const rows = document.querySelectorAll(".product-row");

    function filterProducts() {
        const query = searchInput.value.toLowerCase().trim();
        const selectedCategory = categorySelect.value;

        rows.forEach(row => {
            const productName = row.getAttribute("data-name");
            const productCategory = row.getAttribute("data-category");

            const matchesSearch = productName.includes(query);
            const matchesCategory = selectedCategory === "0" || productCategory === selectedCategory;

            if (matchesSearch && matchesCategory) {
                row.style.display = "";
            } else {
                row.style.display = "none";
            }
        });
    }

    // Eventos para filtragem em tempo real (Instant Search)
    if (searchInput) {
        searchInput.addEventListener("input", filterProducts);
    }
    
    if (categorySelect) {
        categorySelect.addEventListener("change", filterProducts);
    }
});