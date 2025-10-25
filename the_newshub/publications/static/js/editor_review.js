document.getElementById("toggleEditBtn").addEventListener("click", function () {
  const preview = document.getElementById("previewMode");
  const edit = document.getElementById("editMode");
  const btn = this;

  if (preview.style.display === "none") {
    preview.style.display = "block";
    edit.style.display = "none";
    btn.textContent = "Switch to Edit Mode";
  } else {
    preview.style.display = "none";
    edit.style.display = "block";
    btn.textContent = "Switch to Preview Mode";
  }
});
