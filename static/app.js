const form = document.querySelector("#analyzer-form");
const fileInput = document.querySelector("#resume-file");
const dropZone = document.querySelector("#drop-zone");
const uploadTitle = document.querySelector("#upload-title");
const uploadSubtitle = document.querySelector("#upload-subtitle");
const jobDescription = document.querySelector("#job-description");
const charCount = document.querySelector("#char-count");
const submitButton = document.querySelector("#analyze-button");
const buttonLabel = document.querySelector("#button-label");
const statusMessage = document.querySelector("#status-message");
const results = document.querySelector("#results");
const maxFileSize = 10 * 1024 * 1024;
const allowedExtensions = new Set(["pdf", "docx", "txt"]);

function setSelectedFile(file) {
  if (!file) return;
  const extension = file.name.split(".").pop().toLowerCase();
  if (!allowedExtensions.has(extension)) {
    showError("Please choose a PDF, DOCX, or TXT resume.");
    fileInput.value = "";
    return;
  }
  if (file.size > maxFileSize) {
    showError("This file is larger than 10 MB. Choose a smaller resume.");
    fileInput.value = "";
    return;
  }
  uploadTitle.textContent = file.name;
  uploadSubtitle.textContent = `${(file.size / 1024).toFixed(0)} KB · Ready to analyze`;
  dropZone.classList.add("has-file");
  statusMessage.hidden = true;
}

function showError(message) {
  statusMessage.textContent = message;
  statusMessage.classList.remove("is-loading");
  statusMessage.hidden = false;
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  buttonLabel.textContent = isLoading ? "Analyzing…" : "Analyze match";
  if (isLoading) {
    statusMessage.textContent = "Reading the resume and comparing it with the role…";
    statusMessage.classList.add("is-loading");
    statusMessage.hidden = false;
  } else {
    statusMessage.classList.remove("is-loading");
  }
}

function addText(parent, tagName, className, value) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  element.textContent = value;
  parent.append(element);
  return element;
}

function addSkillBlock(parent, title, values, modifier, emptyText) {
  const section = document.createElement("section");
  section.className = "skill-block";
  addText(section, "h4", "", title);
  if (values.length) {
    const list = document.createElement("div");
    list.className = "skill-list";
    for (const value of values) {
      addText(list, "span", `skill-tag${modifier ? ` ${modifier}` : ""}`, value);
    }
    section.append(list);
  } else {
    addText(section, "span", "empty-skills", emptyText);
  }
  parent.append(section);
}

function renderResults(data) {
  const { profile, match } = data;
  results.replaceChildren();

  const heading = document.createElement("div");
  heading.className = "results-heading";
  const titleGroup = document.createElement("div");
  addText(titleGroup, "span", "step-label", "YOUR MATCH");
  addText(titleGroup, "h2", "", "A clearer picture");
  addText(titleGroup, "p", "", "A transparent breakdown to support your review.");
  heading.append(titleGroup);

  const reset = document.createElement("button");
  reset.type = "button";
  reset.className = "reset-button";
  reset.setAttribute("aria-label", "Start a new analysis");
  reset.innerHTML = '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 8a5 5 0 1 0 1.4-3.45L3 6m0-3v3h3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  reset.append(document.createTextNode("New analysis"));
  reset.addEventListener("click", () => {
    form.reset();
    results.hidden = true;
    statusMessage.hidden = true;
    dropZone.classList.remove("has-file");
    uploadTitle.textContent = "Drop a resume here";
    uploadSubtitle.innerHTML = 'or <span>browse files</span>';
    charCount.textContent = "0 / 20,000";
    fileInput.focus();
  });
  heading.append(reset);
  results.append(heading);

  const layout = document.createElement("div");
  layout.className = "results-layout";
  const scoreCard = document.createElement("section");
  scoreCard.className = "score-card";
  scoreCard.setAttribute("aria-label", `Overall fit score: ${match.fit_score} percent`);
  const ring = document.createElement("div");
  ring.className = "score-ring";
  ring.style.setProperty("--score", String(match.fit_score));
  const value = document.createElement("div");
  value.className = "score-value";
  value.append(document.createTextNode(String(match.fit_score)));
  addText(value, "span", "", "%");
  ring.append(value);
  scoreCard.append(ring);
  addText(scoreCard, "h3", "", "Overall fit");
  addText(scoreCard, "p", "", "A weighted comparison, not a verdict.");
  addText(scoreCard, "div", "score-privacy", "Personal contact details are not part of this score.");

  const detail = document.createElement("section");
  detail.className = "detail-card";
  const profileRow = document.createElement("div");
  profileRow.className = "profile-row";
  const candidate = document.createElement("div");
  addText(candidate, "h3", "candidate-name", profile.name || "Candidate profile");
  const contact = document.createElement("div");
  contact.className = "candidate-contact";
  if (profile.email) addText(contact, "span", "", profile.email);
  if (profile.phone) addText(contact, "span", "", profile.phone);
  const facts = [];
  if (profile.experience_years) facts.push(`${profile.experience_years} years detected`);
  if (profile.education) facts.push(profile.education);
  for (const fact of facts) addText(contact, "span", "", fact);
  candidate.append(contact);
  profileRow.append(candidate);
  addText(profileRow, "span", "file-name", data.filename);
  detail.append(profileRow);

  addSkillBlock(detail, "MATCHED SKILLS", match.matched_skills, "", "No matching catalogued skills found.");
  addSkillBlock(detail, "SKILL GAPS TO REVIEW", match.missing_skills, "missing", "No catalogued skill gaps found.");
  addSkillBlock(detail, "INFERRED FROM RELATED TOOLS", match.inferred_skills, "inferred", "No skills inferred.");

  addText(detail, "h3", "breakdown-title", "How the score is built");
  const breakdown = document.createElement("div");
  breakdown.className = "breakdown-list";
  for (const item of match.components) {
    const row = document.createElement("div");
    row.className = "breakdown-item";
    addText(row, "span", "breakdown-label", `${item.name} · ${item.weight}%`);
    const track = document.createElement("div");
    track.className = "bar-track";
    const fill = document.createElement("div");
    fill.className = "bar-fill";
    fill.style.width = `${item.score}%`;
    track.append(fill);
    row.append(track);
    addText(row, "span", "breakdown-score", `${item.score}%`);
    addText(row, "span", "breakdown-detail", item.detail);
    breakdown.append(row);
  }
  detail.append(breakdown);

  layout.append(scoreCard, detail);
  results.append(layout);
  addText(results, "p", "results-notice", data.notice);
  results.hidden = false;
  results.scrollIntoView({ behavior: "smooth", block: "start" });
}

fileInput.addEventListener("change", () => setSelectedFile(fileInput.files[0]));
jobDescription.addEventListener("input", () => {
  charCount.textContent = `${jobDescription.value.length.toLocaleString()} / 20,000`;
});

for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("is-dragging");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("is-dragging");
  });
}
dropZone.addEventListener("drop", (event) => {
  const [file] = event.dataTransfer.files;
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  setSelectedFile(file);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = fileInput.files[0];
  if (!file) {
    showError("Choose a resume file to continue.");
    fileInput.focus();
    return;
  }
  if (jobDescription.value.trim().length < 30) {
    showError("Add a little more detail to the job description (at least 30 characters).");
    jobDescription.focus();
    return;
  }

  const formData = new FormData(form);
  setLoading(true);
  results.hidden = true;
  try {
    const response = await fetch("/api/analyze", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "The resume could not be analyzed. Please try again.");
    }
    renderResults(data);
    statusMessage.hidden = true;
  } catch (error) {
    showError(error instanceof Error ? error.message : "Something went wrong. Please try again.");
  } finally {
    setLoading(false);
  }
});
