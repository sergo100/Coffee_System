// Подтверждение удаления
function confirmDelete(name) {
    return confirm("Вы точно хотите удалить: " + name + "?");
}

// Простые микроанимации
window.onload = function() {
    let tables = document.querySelectorAll("table");
    tables.forEach(t => {
        t.style.opacity = 0;
        t.style.transition = "opacity 0.5s";
        setTimeout(() => { t.style.opacity = 1; }, 100);
    });
};
