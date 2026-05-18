const artworkIds = "01 02 03 04 05 06 07 08 09 10 11 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 99".split(" ");

const titleOverrides = {
  "01": "Taj Mahal",
};

const artworkData = artworkIds.map((id, index) => ({
  id,
  title: titleOverrides[id] ?? `Artwork ${id}`,
  description:
    index === 0
      ? "Acrylic on canvas with dimensional texture from the Pinkal Art collection."
      : "Original work from the Pinkal Art collection.",
  thumb: `images/thumbs/${id}.jpg`,
  full: `images/fulls/${id}.jpg`,
}));

const state = {
  artworks: [...artworkData],
  activeIndex: 0,
};

const galleryGrid = document.getElementById("galleryGrid");
const artworkCardTemplate = document.getElementById("artworkCardTemplate");
const artworkCountTargets = document.querySelectorAll("[data-artwork-count]");
const artworkReference = document.getElementById("artworkReference");
const shuffleButton = document.getElementById("shuffleButton");
const contactForm = document.getElementById("contactForm");
const formStatus = document.getElementById("formStatus");
const submitButton = contactForm.querySelector(".submit-button");
const lightbox = document.getElementById("lightbox");
const lightboxImage = document.getElementById("lightboxImage");
const lightboxTitle = document.getElementById("lightboxTitle");
const lightboxDescription = document.getElementById("lightboxDescription");
const closeLightboxButton = document.getElementById("closeLightbox");
const prevArtworkButton = document.getElementById("prevArtwork");
const nextArtworkButton = document.getElementById("nextArtwork");
const inquireArtworkButton = document.getElementById("inquireArtwork");

function updateArtworkCount() {
  artworkCountTargets.forEach((target) => {
    target.textContent = String(state.artworks.length);
  });
}

function createArtworkCard(artwork, index) {
  const fragment = artworkCardTemplate.content.cloneNode(true);
  const card = fragment.querySelector(".artwork-card");
  const openButton = fragment.querySelector(".artwork-card__open");
  const image = fragment.querySelector(".artwork-card__image");
  const title = fragment.querySelector(".artwork-card__title");
  const inquireButton = fragment.querySelector(".artwork-card__inquire");

  image.src = artwork.thumb;
  image.alt = `${artwork.title} by Pinkal Art`;
  title.textContent = artwork.title;

  openButton.addEventListener("click", () => openLightbox(index));
  inquireButton.addEventListener("click", () => focusInquiry(artwork));

  card.dataset.artworkId = artwork.id;

  return fragment;
}

function renderGallery() {
  galleryGrid.replaceChildren();

  const fragment = document.createDocumentFragment();

  state.artworks.forEach((artwork, index) => {
    fragment.appendChild(createArtworkCard(artwork, index));
  });

  galleryGrid.appendChild(fragment);
  updateArtworkCount();
}

function openLightbox(index) {
  state.activeIndex = index;
  const artwork = state.artworks[index];

  lightboxImage.src = artwork.full;
  lightboxImage.alt = `${artwork.title} full view`;
  lightboxTitle.textContent = artwork.title;
  lightboxDescription.textContent = artwork.description;
  lightbox.hidden = false;
  lightbox.setAttribute("aria-hidden", "false");
  document.body.classList.add("is-locked");
}

function closeLightbox() {
  lightbox.hidden = true;
  lightbox.setAttribute("aria-hidden", "true");
  document.body.classList.remove("is-locked");
}

function stepArtwork(direction) {
  const nextIndex = (state.activeIndex + direction + state.artworks.length) % state.artworks.length;
  openLightbox(nextIndex);
}

function focusInquiry(artwork) {
  artworkReference.value = artwork.title;
  closeLightbox();
  document.getElementById("contact").scrollIntoView({ behavior: "smooth", block: "start" });
  artworkReference.focus();
}

function shuffleArtworks() {
  const shuffled = [...state.artworks];

  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));
    [shuffled[index], shuffled[randomIndex]] = [shuffled[randomIndex], shuffled[index]];
  }

  state.artworks = shuffled;
  renderGallery();
}

async function handleFormSubmit(event) {
  event.preventDefault();

  formStatus.className = "form-status";
  formStatus.textContent = "Sending your message...";
  submitButton.disabled = true;

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
    formStatus.textContent = "Message sent. Pinkal Art will get back to you through the inquiry inbox.";
  } catch {
    formStatus.className = "form-status is-error";
    formStatus.innerHTML =
      'The form could not be sent right now. Please try again in a moment or use <a href="https://instagram.com/pinkal_art_kunst" target="_blank" rel="noreferrer">Instagram</a>.';
  } finally {
    submitButton.disabled = false;
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
      threshold: 0.15,
    }
  );

  revealTargets.forEach((target) => observer.observe(target));
}

shuffleButton.addEventListener("click", shuffleArtworks);
contactForm.addEventListener("submit", handleFormSubmit);
closeLightboxButton.addEventListener("click", closeLightbox);
prevArtworkButton.addEventListener("click", () => stepArtwork(-1));
nextArtworkButton.addEventListener("click", () => stepArtwork(1));
inquireArtworkButton.addEventListener("click", () => focusInquiry(state.artworks[state.activeIndex]));

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

renderGallery();
setupRevealAnimation();