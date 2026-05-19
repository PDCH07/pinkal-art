const pieces = [...document.querySelectorAll(".piece")].map((piece, index) => {
  const link = piece.querySelector("[data-lightbox]");
  const image = link.querySelector("img");

  return {
    index,
    id: piece.dataset.index,
    title: piece.dataset.title,
    description: piece.dataset.description,
    full: link.getAttribute("href"),
    alt: image.alt,
    link,
  };
});

const state = {
  activeIndex: 0,
};

const artworkReference = document.getElementById("artworkReference");
const contactForm = document.getElementById("contactForm");
const formStatus = document.getElementById("formStatus");
const lightbox = document.getElementById("lightbox");
const lightboxImage = document.getElementById("lightboxImage");
const lightboxIndex = document.getElementById("lightboxIndex");
const lightboxTitle = document.getElementById("lightboxTitle");
const lightboxDescription = document.getElementById("lightboxDescription");
const closeLightboxButton = document.getElementById("closeLightbox");
const prevArtworkButton = document.getElementById("prevArtwork");
const nextArtworkButton = document.getElementById("nextArtwork");
const lightboxInquireButton = document.getElementById("lightboxInquire");

function openLightbox(index) {
  const artwork = pieces[index];

  state.activeIndex = index;
  lightboxImage.src = artwork.full;
  lightboxImage.alt = artwork.alt;
  lightboxIndex.textContent = artwork.id;
  lightboxTitle.textContent = artwork.title;
  lightboxDescription.textContent = artwork.description;
  lightbox.hidden = false;
  lightbox.setAttribute("aria-hidden", "false");
  document.body.classList.add("is-locked");
}

function closeLightbox() {
  lightbox.hidden = true;
  lightbox.setAttribute("aria-hidden", "true");
  lightboxImage.removeAttribute("src");
  document.body.classList.remove("is-locked");
}

function stepArtwork(direction) {
  const nextIndex = (state.activeIndex + direction + pieces.length) % pieces.length;
  openLightbox(nextIndex);
}

function fillInquiry(title) {
  artworkReference.value = title;
  closeLightbox();
  document.getElementById("contact").scrollIntoView({ behavior: "smooth", block: "start" });
  artworkReference.focus();
}

async function handleFormSubmit(event) {
  event.preventDefault();

  formStatus.className = "form-status";
  formStatus.textContent = "Sending your message...";

  try {
    const response = await fetch(contactForm.action, {
      method: "POST",
      body: new FormData(contactForm),
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      throw new Error("Request failed");
    }

    contactForm.reset();
    formStatus.className = "form-status is-success";
    formStatus.textContent = "Message sent. Pinkal Art will reply through the inquiry inbox.";
  } catch {
    formStatus.className = "form-status is-error";
    formStatus.innerHTML =
      'The form could not be sent right now. Please try again or use <a href="https://instagram.com/pinkal_art_kunst" target="_blank" rel="noreferrer">Instagram</a>.';
  }
}

function setupRevealAnimation() {
  const revealTargets = document.querySelectorAll("[data-reveal]");

  if (!("IntersectionObserver" in window)) {
    revealTargets.forEach((target) => target.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    {
      threshold: 0.12,
    }
  );

  revealTargets.forEach((target) => observer.observe(target));
}

pieces.forEach((artwork, index) => {
  artwork.link.addEventListener("click", (event) => {
    event.preventDefault();
    openLightbox(index);
  });
});

contactForm.addEventListener("submit", handleFormSubmit);
closeLightboxButton.addEventListener("click", closeLightbox);
prevArtworkButton.addEventListener("click", () => stepArtwork(-1));
nextArtworkButton.addEventListener("click", () => stepArtwork(1));
lightboxInquireButton.addEventListener("click", () => fillInquiry(pieces[state.activeIndex].title));

lightbox.addEventListener("click", (event) => {
  if (event.target === lightbox) {
    closeLightbox();
  }
});

document.addEventListener("keydown", (event) => {
  if (lightbox.hidden) {
    return;
  }

  if (event.key === "Escape") {
    closeLightbox();
  }

  if (event.key === "ArrowLeft") {
    stepArtwork(-1);
  }

  if (event.key === "ArrowRight") {
    stepArtwork(1);
  }
});

setupRevealAnimation();