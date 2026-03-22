document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-dropzone]").forEach((card) => {
    const zone = card.querySelector(".dropzone");
    const input = card.querySelector('input[type="file"]');
    if (!zone || !input) {
      return;
    }

    zone.addEventListener("click", () => input.click());

    ["dragenter", "dragover"].forEach((eventName) => {
      zone.addEventListener(eventName, (event) => {
        event.preventDefault();
        zone.classList.add("drag-over");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      zone.addEventListener(eventName, (event) => {
        event.preventDefault();
        zone.classList.remove("drag-over");
      });
    });

    zone.addEventListener("drop", (event) => {
      if (!event.dataTransfer?.files?.length) {
        return;
      }
      input.files = event.dataTransfer.files;
    });
  });
});
