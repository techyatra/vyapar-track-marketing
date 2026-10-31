// Shared icon set + keyword matcher for all VyaparTrack visual templates.
// Hand-drawn inline SVGs (stroke-based, brand colors) -- no icon-font or
// external request, so it works offline the same as everything else here.
// Keeps icon selection content-driven: the model's own text decides which
// icon shows, instead of hardcoding one icon per scene/slide type.

const VT_ICONS = {
  boxes: `<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M24 6L40 14V34L24 42L8 34V14L24 6Z" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round"/><path d="M8 14L24 22L40 14" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round"/><path d="M24 22V42" stroke="currentColor" stroke-width="2.5"/></svg>`,
  truck: `<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="4" y="14" width="24" height="18" rx="1.5" stroke="currentColor" stroke-width="2.5"/><path d="M28 20H38L44 26V32H28V20Z" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round"/><circle cx="13" cy="36" r="4" stroke="currentColor" stroke-width="2.5"/><circle cx="35" cy="36" r="4" stroke="currentColor" stroke-width="2.5"/></svg>`,
  receipt: `<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 4H36V44L31 40L26 44L22 40L18 44L12 40V4Z" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round"/><path d="M18 15H30M18 23H30M18 31H25" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg>`,
  percent: `<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="24" cy="24" r="19" stroke="currentColor" stroke-width="2.5"/><circle cx="18" cy="18" r="3.5" stroke="currentColor" stroke-width="2.5"/><circle cx="30" cy="30" r="3.5" stroke="currentColor" stroke-width="2.5"/><path d="M17 31L31 17" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg>`,
  chart: `<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M6 40H42" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><rect x="11" y="26" width="7" height="14" rx="1" stroke="currentColor" stroke-width="2.5"/><rect x="22" y="18" width="7" height="22" rx="1" stroke="currentColor" stroke-width="2.5"/><rect x="33" y="9" width="7" height="31" rx="1" stroke="currentColor" stroke-width="2.5"/></svg>`,
  building: `<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="9" y="8" width="20" height="36" rx="1.5" stroke="currentColor" stroke-width="2.5"/><rect x="29" y="18" width="12" height="26" rx="1.5" stroke="currentColor" stroke-width="2.5"/><path d="M14 15H16M21 15H23M14 22H16M21 22H23M14 29H16M21 29H23" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg>`,
  check: `<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="24" cy="24" r="19" stroke="currentColor" stroke-width="2.5"/><path d="M15 24.5L21 30.5L33 17.5" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  cross: `<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="24" cy="24" r="19" stroke="currentColor" stroke-width="2.5"/><path d="M17 17L31 31M31 17L17 31" stroke="currentColor" stroke-width="2.8" stroke-linecap="round"/></svg>`,
  clock: `<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="24" cy="24" r="19" stroke="currentColor" stroke-width="2.5"/><path d="M24 13V24L32 29" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  shield: `<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M24 5L40 11V23C40 33 33 40.5 24 44C15 40.5 8 33 8 23V11L24 5Z" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round"/><path d="M17 23.5L22 28.5L31 18.5" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  phone: `<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="13" y="4" width="22" height="40" rx="3" stroke="currentColor" stroke-width="2.5"/><path d="M21 10H27" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><path d="M13 36H35" stroke="currentColor" stroke-width="2.5"/></svg>`,
  spark: `<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M24 4L28.5 19.5L44 24L28.5 28.5L24 44L19.5 28.5L4 24L19.5 19.5L24 4Z" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round"/></svg>`,
};

const VT_ICON_KEYWORDS = [
  [/firm|godown|multi|branch|gstin/i, "building"],
  [/gst|tax|cgst|sgst|igst|hsn/i, "percent"],
  [/stock|inventory|fifo|batch|crate|maal|warehouse/i, "boxes"],
  [/truck|dispatch|delivery|beat|salesman/i, "truck"],
  [/bill|invoice|estimate|receipt/i, "receipt"],
  [/margin|profit|price|grn|cost|revenue/i, "chart"],
  [/time|hour|fast|instant|minute/i, "clock"],
  [/safe|secure|lock|compliance|guarantee/i, "shield"],
  [/app|dashboard|screen|mobile|phone/i, "phone"],
];

function vtPickIcon(text) {
  const t = String(text || "");
  for (const [re, name] of VT_ICON_KEYWORDS) {
    if (re.test(t)) return VT_ICONS[name];
  }
  return VT_ICONS.spark;
}

function vtIconHtml(text, sizeClass) {
  return `<span class="${sizeClass || "vt-icon"}">${vtPickIcon(text)}</span>`;
}
