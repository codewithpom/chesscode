// The few fixed words the scenes draw, outside the spec. Hindi keeps the chess words the way the channel's
// Hindi lines do (docs/SPEC.md section 8, joke rule 3); the owner should confirm the wording.
export const strings = {
  en: { turningPoint: "Turning point", accuracy: "Accuracy", signOffWave: "See you next game!", signOffPoint: "More over there" },
  hi: { turningPoint: "टर्निंग पॉइंट", accuracy: "एक्यूरेसी", signOffWave: "अगले गेम में मिलते हैं!", signOffPoint: "और गेम वहाँ देखो" },
} as const;
