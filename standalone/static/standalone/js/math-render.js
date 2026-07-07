(function () {
  const literalUnicodeEscapePattern = /\\u([0-9a-fA-F]{4})|\\U([0-9a-fA-F]{8})/g;
  const mathDelimitedPattern = /(?:\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\))/g;
  const inlineEquationPatternSource = String.raw`\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)?(?:\s+[A-Za-z][A-Za-z0-9]*){0,5}\s*=\s*.+?(?=(?:[.?!;:](?:\s|$))|$)`;
  const greekTexMap = {
    α: "\\alpha",
    β: "\\beta",
    γ: "\\gamma",
    δ: "\\delta",
    Δ: "\\Delta",
    ε: "\\epsilon",
    θ: "\\theta",
    λ: "\\lambda",
    μ: "\\mu",
    π: "\\pi",
    σ: "\\sigma",
    φ: "\\phi",
    ω: "\\omega",
  };
  const superscriptDigits = {
    "-": "⁻",
    "+": "⁺",
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
  };
  const superscriptDigitLookup = Object.fromEntries(
    Object.entries(superscriptDigits).map(([plainText, superscriptText]) => [superscriptText, plainText]),
  );
  const mathFunctionNames = [
    "radians",
    "degrees",
    "log10",
    "sqrt",
    "asin",
    "acos",
    "atan",
    "sin",
    "cos",
    "tan",
    "log",
    "ln",
    "exp",
    "abs",
  ];
  const mathFunctionTex = {
    radians: "\\operatorname{radians}",
    degrees: "\\operatorname{degrees}",
    log10: "\\log_{10}",
    asin: "\\arcsin",
    acos: "\\arccos",
    atan: "\\arctan",
    sin: "\\sin",
    cos: "\\cos",
    tan: "\\tan",
    log: "\\log",
    ln: "\\ln",
    exp: "\\exp",
    abs: "\\operatorname{abs}",
  };
  const excelFormulaBoundaryWords = new Set([
    "after",
    "as",
    "because",
    "before",
    "by",
    "during",
    "for",
    "from",
    "how",
    "if",
    "in",
    "into",
    "is",
    "means",
    "on",
    "returns",
    "shows",
    "that",
    "to",
    "used",
    "using",
    "what",
    "when",
    "where",
    "which",
    "while",
    "why",
    "with",
  ]);

  function hasKatexRenderer() {
    return typeof window.renderMathInElement === "function";
  }

  function normalizeRenderOptions(options) {
    if (!options || typeof options !== "object") {
      return {};
    }
    return options;
  }

  function renderMath(container) {
    if (!container || !hasKatexRenderer()) {
      return;
    }
    window.renderMathInElement(container, {
      delimiters: [
        { left: "\\(", right: "\\)", display: false },
        { left: "\\[", right: "\\]", display: true },
      ],
      throwOnError: false,
      strict: "ignore",
      ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code"],
      ignoredClasses: ["katex", "katex-display"],
    });
  }

  function decodeLiteralUnicodeEscapes(text) {
    return String(text || "").replace(literalUnicodeEscapePattern, (match, shortCodepoint, longCodepoint) => {
      const codepoint = shortCodepoint || longCodepoint;
      const parsed = Number.parseInt(codepoint, 16);
      return Number.isFinite(parsed) ? String.fromCodePoint(parsed) : match;
    });
  }

  function formatScientificNotationExponent(exponentText) {
    return normalizeScientificNotationExponentText(exponentText).replace(/^\+/, "").replace(/^-/, "−");
  }

  function normalizeScientificNotationExponentText(exponentText) {
    return String(exponentText || "")
      .replace(/\s+/g, "")
      .replace(/^−/, "-")
      .replace(/^⁻/, "-")
      .replace(/^＋/, "+")
      .replace(/^⁺/, "+");
  }

  function scientificNotationNumericValue(mantissa, exponent) {
    const normalizedExponent = normalizeScientificNotationExponentText(exponent);
    const value = Number(`${mantissa}e${normalizedExponent}`);
    return Number.isFinite(value) ? value : null;
  }

  function shouldUseScientificNotation(mantissa, exponent) {
    const numericValue = scientificNotationNumericValue(mantissa, exponent);
    if (numericValue === null || numericValue === 0) {
      return false;
    }
    const absoluteValue = Math.abs(numericValue);
    return absoluteValue < 1e-3 || absoluteValue >= 1e4;
  }

  function decimalTextFromScientificNotation(mantissa, exponent) {
    const numericValue = scientificNotationNumericValue(mantissa, exponent);
    return numericValue === null ? `${mantissa}e${exponent}` : `${numericValue}`;
  }

  function appendScientificNotation(target, mantissa, exponent) {
    const wrapper = document.createElement("span");
    wrapper.className = "preview-scientific-notation";

    const base = document.createElement("span");
    base.className = "preview-scientific-notation-base";
    base.textContent = `${mantissa} × 10`;

    const superscript = document.createElement("sup");
    superscript.className = "preview-scientific-notation-exponent";
    superscript.textContent = formatScientificNotationExponent(exponent);

    wrapper.append(base, superscript);
    target.appendChild(wrapper);
  }

  function decodeSuperscriptExponent(text) {
    return Array.from(String(text || "")).map((character) => superscriptDigitLookup[character] || character).join("");
  }

  function appendTextWithUnitPowers(target, text) {
    const sourceText = String(text || "");
    const powerPattern = /([A-Za-zµμΩ%])\^([+\-−]?\d+)/g;
    let lastIndex = 0;

    sourceText.replace(powerPattern, (match, base, exponent, offset) => {
      const plainPrefix = sourceText.slice(lastIndex, offset);
      if (plainPrefix) {
        target.appendChild(document.createTextNode(plainPrefix));
      }

      target.appendChild(document.createTextNode(base));
      const superscript = document.createElement("sup");
      superscript.className = "preview-inline-superscript";
      superscript.textContent = formatScientificNotationExponent(exponent);
      target.appendChild(superscript);

      lastIndex = offset + match.length;
      return match;
    });

    const trailing = sourceText.slice(lastIndex);
    if (trailing) {
      target.appendChild(document.createTextNode(trailing));
    }
  }

  function appendTextWithScientificNotation(target, text) {
    const sourceText = String(text || "")
      .replace(/(\d)(eV|keV|MeV|GeV)\b/g, "$1 $2")
      .replace(/,\s*and(?=\S)/gi, ", and ")
      .replace(/\band(?=\d)/gi, "and ");
    const scientificPattern = /(^|[^A-Za-z0-9_\\])([-+]?(?:\d+(?:\.\d+)?|\.\d+))\s*(?:[eE]\s*([+\-−]?\d+)|×\s*10(?:\^([+\-−]?\d+)|([⁻⁺⁰¹²³⁴⁵⁶⁷⁸⁹]+)))(?=($|[^A-Za-z0-9_]))/g;
    let lastIndex = 0;

    sourceText.replace(scientificPattern, (match, prefix, mantissa, rawExponent, plainPowerExponent, superscriptExponent, _suffix, offset) => {
      const plainPrefix = sourceText.slice(lastIndex, offset);
      if (plainPrefix) {
        appendTextWithUnitPowers(target, plainPrefix);
      }
      if (prefix) {
        appendTextWithUnitPowers(target, prefix);
      }
      const exponent = normalizeScientificNotationExponentText(
        rawExponent || plainPowerExponent || decodeSuperscriptExponent(superscriptExponent),
      );
      if (shouldUseScientificNotation(mantissa, exponent)) {
        appendScientificNotation(target, mantissa, exponent);
      } else {
        appendTextWithUnitPowers(target, decimalTextFromScientificNotation(mantissa, exponent));
      }
      lastIndex = offset + match.length;
      return match;
    });

    const trailing = sourceText.slice(lastIndex);
    if (trailing) {
      appendTextWithUnitPowers(target, trailing);
    }
  }

  function normalizeScientificNotationMath(text) {
    return String(text || "").replace(
      /(^|[^A-Za-z0-9_\\])([-+]?(?:\d+(?:\.\d+)?|\.\d+))\s*(?:[eE]\s*([+\-−]?\d+)|×\s*10\^([+\-−]?\d+))(?=($|[^A-Za-z0-9_]))/g,
      (match, prefix, mantissa, rawExponent, powerExponent) => {
        const exponent = normalizeScientificNotationExponentText(rawExponent || powerExponent);
        return (
          shouldUseScientificNotation(mantissa, exponent)
            ? `${prefix}${mantissa} \\times 10^{${Number.parseInt(exponent, 10)}}`
            : `${prefix}${decimalTextFromScientificNotation(mantissa, exponent)}`
        );
      },
    );
  }

  function replaceGreekCharacters(text) {
    return Array.from(String(text || "")).map((character) => greekTexMap[character] || character).join("");
  }

  function isIdentifierBoundary(character) {
    return !character || !/[A-Za-z0-9_\\]/.test(character);
  }

  function findMatchingParen(text, openIndex) {
    let depth = 0;
    for (let index = openIndex; index < text.length; index += 1) {
      if (text[index] === "(") {
        depth += 1;
      } else if (text[index] === ")") {
        depth -= 1;
        if (depth === 0) {
          return index;
        }
      }
    }
    return -1;
  }

  function mathFunctionLabel(name) {
    return mathFunctionTex[name] || `\\operatorname{${name}}`;
  }

  function formatAngleTex(argumentTex) {
    const normalized = String(argumentTex || "").trim();
    if (!normalized) {
      return "";
    }
    if (/^[A-Za-z0-9\\{}_^.-]+$/.test(normalized)) {
      return `${normalized}^{\\circ}`;
    }
    return `\\left(${normalized}\\right)^{\\circ}`;
  }

  function wrapRomanMathPhrase(phrase) {
    const normalized = String(phrase || "").trim();
    if (!normalized) {
      return "";
    }
    if (normalized.includes("\\")) {
      return normalized;
    }
    if (/^[A-Za-z]$/.test(normalized)) {
      return normalized;
    }
    if (/^(?:sin|cos|tan|asin|acos|atan|ln|log10|log|exp|abs|sqrt|radians|degrees|pi|e)$/i.test(normalized)) {
      return normalized;
    }
    return `\\mathrm{${normalized.replace(/\s+/g, "\\ ")}}`;
  }

  function romanizeWordPhrases(text) {
    return String(text || "").replace(
      /(^|[=+\-*/×÷−(){}\[\],])\s*([A-Za-z][A-Za-z]*(?:\s+[A-Za-z][A-Za-z]*)*)(?=\s*(?:[=+\-*/×÷−(){}\[\],]|$))/g,
      (match, prefix, phrase, offset, source) => {
        if (prefix === "{" && /\\[A-Za-z]+$/.test(source.slice(Math.max(0, offset - 24), offset))) {
          return match;
        }
        return `${prefix}${wrapRomanMathPhrase(phrase)}`;
      },
    );
  }

  function normalizeEquationExpression(expression) {
    const source = String(expression || "");
    const equalsIndex = source.indexOf("=");
    if (equalsIndex < 0) {
      return source.trim();
    }

    let left = source.slice(0, equalsIndex).trim();
    const right = source.slice(equalsIndex + 1).trim();

    left = left
      .replace(/^(?:the\s+)?(?:formula|equation|relationship|expression|law)\s*[:\-]?\s*/i, "")
      .replace(/^(?:the\s+)?(?:formula|equation|relationship|expression|law)\s+(?:is|for|becomes)\s+/i, "")
      .replace(/^(?:this|that|it)\s+(?:is|gives|becomes)\s+/i, "")
      .trim();

    const leftWords = left.split(/\s+/).filter(Boolean);
    if (leftWords.length > 4) {
      left = leftWords.slice(-2).join(" ");
    }

    return `${left} = ${right}`.trim();
  }

  function splitEquationExpression(expression) {
    const source = String(expression || "");
    const proseTailPattern = /,\s*(?=(?:calculate|determine|estimate|find|compute|work out|show|state|identify|explain|what|which|how|when|where|why)\b)/i;
    const match = proseTailPattern.exec(source);
    if (!match || match.index < 0) {
      return {
        equationText: source,
        trailingText: "",
      };
    }
    return {
      equationText: source.slice(0, match.index).trimEnd(),
      trailingText: source.slice(match.index),
    };
  }

  function replaceBarePiInMath(text) {
    return String(text || "").replace(/(^|[^\\A-Za-z])pi(?=([^A-Za-z]|$))/g, (match, prefix) => `${prefix}\\pi`);
  }

  function normalizeStoredMathBody(body) {
    let normalized = decodeLiteralUnicodeEscapes(body);

    for (let iteration = 0; iteration < 4; iteration += 1) {
      const next = normalized
        .replace(/^\\\[\s*([\s\S]*?)\s*\\\]\s*$/g, "$1")
        .replace(/^\\\(\s*([\s\S]*?)\s*\\\)\s*([,.;:]?)\s*$/g, "$1$2")
        .replace(/\\\\(?=[A-Za-z,;:.!])/g, "\\");
      if (next === normalized) {
        break;
      }
      normalized = next;
    }

    for (let iteration = 0; iteration < 4; iteration += 1) {
      const next = normalized
        .replace(/\\operatorname\{radians\}\\left\(([^()]*)\\right\)/g, (match, argument) => formatAngleTex(argument))
        .replace(/\bradians\(([^()]*)\)/g, (match, argument) => formatAngleTex(convertInlineExpressionToTex(argument)));
      if (next === normalized) {
        break;
      }
      normalized = next;
    }

    normalized = replaceBarePiInMath(normalized);
    normalized = normalizeScientificNotationMath(normalized);
    return normalized;
  }

  function displayMathBodyLooksLikeProse(body) {
    const source = String(body || "").trim();
    if (!source) {
      return false;
    }
    const lowered = source.toLowerCase();
    if (
      lowered.startsWith("-")
      || lowered.startsWith("*")
      || /^(?:correct\.|incorrect\.|let |here,|so |therefore|using |substituting|rounding|given:|measured |total |mass defect|convert to energy)/.test(lowered)
    ) {
      return true;
    }
    const proseCheck = decodeLiteralUnicodeEscapes(source)
      .replace(/\\\([\s\S]*?\\\)/g, " ")
      .replace(/\\text\{[^}]*\}/g, " ")
      .replace(/\\mathrm\{[^}]*\}/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    const words = proseCheck.match(/[A-Za-z]{2,}/g) || [];
    if (words.length >= 5) {
      return true;
    }
    return words.length >= 3 && /[.,:]/.test(proseCheck);
  }

  function normalizeStandaloneMathBlockText(blockText) {
    const normalized = decodeLiteralUnicodeEscapes(blockText).trim();
    if (!normalized) {
      return "";
    }
    if (normalized.startsWith("\\[") && normalized.endsWith("\\]")) {
      return `\\[${normalizeStoredMathBody(normalized.slice(2, -2))}\\]`;
    }
    if (normalized.startsWith("\\(") && normalized.endsWith("\\)")) {
      return `\\(${normalizeStoredMathBody(normalized.slice(2, -2))}\\)`;
    }
    return `\\[${normalizeStoredMathBody(normalized)}\\]`;
  }

  function normalizeNestedDisplayMathWrappers(text) {
    let normalized = String(text || "");
    for (let iteration = 0; iteration < 6; iteration += 1) {
      const next = normalized
        .replace(/\\\[\s*(\\\[[\s\S]*?\\\])\s*\\\]/g, "$1")
        .replace(
          /\\\[\s*([\s\S]*?)\s*\\\]/g,
          (match, body) => (
            displayMathBodyLooksLikeProse(body)
              ? String(body || "").trim()
              : `\\[${String(body || "").trim()}\\]`
          ),
        );
      if (next === normalized) {
        break;
      }
      normalized = next;
    }
    return normalized;
  }

  function looksLikeStandaloneLatexMathBlock(blockText) {
    const normalized = decodeLiteralUnicodeEscapes(blockText).trim();
    if (!normalized) {
      return false;
    }
    if (
      normalized.startsWith("\\[")
      || normalized.startsWith("\\(")
      || /:$/.test(normalized)
      || /^(?:Correct|Incorrect|Let|Here,|So |Therefore|Using |Substituting|Rounding)\b/i.test(normalized)
    ) {
      return false;
    }
    const hasMathSignal = /[=^_]|\\(?:frac|times|approx|sqrt|mathrm|text|pi|theta|omega|lambda|mu|rho|sigma|phi|Delta|delta|cdot|sin|cos|tan|ln|log|exp)\b|[×÷]/.test(normalized);
    if (!hasMathSignal) {
      return false;
    }
    const compactEquation = /^[A-Za-z0-9α-ωΑ-Ω\\{}\[\]_^=+\-−×÷*/().,|\s]+$/.test(normalized);
    if (!compactEquation) {
      return false;
    }
    const naturalWords = normalized
      .replace(/\\[A-Za-z]+/g, " ")
      .match(/[A-Za-z]{3,}/g) || [];
    return naturalWords.length <= 6;
  }

  function normalizeDelimitedMath(text) {
    const decoded = decodeLiteralUnicodeEscapes(text);
    return decoded.replace(/(\\\[|\\\()([\s\S]*?)(\\\]|\\\))/g, (match, left, body, right) => {
      return `${left}${normalizeStoredMathBody(body)}${right}`;
    });
  }

  function replaceMathFunctionCalls(text) {
    let output = "";
    let cursor = 0;

    while (cursor < text.length) {
      let replaced = false;

      for (const name of mathFunctionNames) {
        if (text.slice(cursor, cursor + name.length).toLowerCase() !== name) {
          continue;
        }
        if (!isIdentifierBoundary(text[cursor - 1])) {
          continue;
        }

        let openIndex = cursor + name.length;
        while (/\s/.test(text[openIndex] || "")) {
          openIndex += 1;
        }
        if (text[openIndex] !== "(") {
          continue;
        }

        const closeIndex = findMatchingParen(text, openIndex);
        if (closeIndex < 0) {
          continue;
        }

        const innerExpression = text.slice(openIndex + 1, closeIndex);
        const innerTex = convertInlineExpressionToTex(innerExpression);
        if (name === "sqrt") {
          output += `\\sqrt{${innerTex}}`;
        } else if (name === "abs") {
          output += `\\left|${innerTex}\\right|`;
        } else if (name === "radians") {
          output += formatAngleTex(innerTex);
        } else {
          output += `${mathFunctionLabel(name)}\\left(${innerTex}\\right)`;
        }
        cursor = closeIndex + 1;
        replaced = true;
        break;
      }

      if (!replaced) {
        output += text[cursor];
        cursor += 1;
      }
    }

    return output;
  }

  function replaceBareMathFunctions(text) {
    return String(text || "").replace(
      /\b(?:sin|cos|tan|asin|acos|atan|ln|log10|log|exp|abs|radians|degrees)\b/gi,
      (match, offset, source) => {
        if (!isIdentifierBoundary(source[offset - 1])) {
          return match;
        }
        return mathFunctionLabel(match.toLowerCase());
      },
    );
  }

  function replacePiConstant(text) {
    return String(text || "").replace(/\bpi\b/gi, (match, offset, source) => {
      if (!isIdentifierBoundary(source[offset - 1])) {
        return match;
      }
      return "\\pi";
    });
  }

  function replaceIdentifierSubscripts(text) {
    return String(text || "")
      .replace(
        /\b([A-Za-z][A-Za-z0-9]*)_([A-Za-z0-9]+)\b/g,
        (match, base, subscript) => {
          const baseTex = base.length === 1 ? base : `\\mathrm{${base}}`;
          return `${baseTex}_{\\mathrm{${subscript}}}`;
        },
      )
      .replace(
        /\b([A-Za-z]+)(\d+)\b/g,
        (match, base, subscript) => {
          const baseTex = base.length === 1 ? base : `\\mathrm{${base}}`;
          return `${baseTex}_{${subscript}}`;
        },
      );
  }

  function normalizeEquationTrailingText(text) {
    const normalized = String(text || "").trim();
    if (!normalized) {
      return "";
    }

    const leadingVerbPattern = /^,\s*(calculate|determine|estimate|find|compute|work out|show|state|identify|explain|what|which|how|when|where|why)\b/i;
    const match = leadingVerbPattern.exec(normalized);
    if (!match) {
      return ` ${normalized}`;
    }

    const verb = match[1];
    const sentenceTail = normalized
      .slice(match[0].length)
      .replace(/^\s+/, "");

    return `. ${verb.charAt(0).toUpperCase()}${verb.slice(1)}${sentenceTail ? ` ${sentenceTail}` : ""}`;
  }

  function convertInlineExpressionToTex(expression) {
    let normalized = decodeLiteralUnicodeEscapes(expression).replace(/\s+/g, " ").trim();
    if (!normalized) {
      return "";
    }
    normalized = normalized.replace(/\\(alpha|beta|gamma|delta|epsilon|theta|lambda|mu|pi|sigma|phi|omega)(?=[A-Za-z])/gi, "\\$1 ");
    normalized = normalizeScientificNotationMath(normalized);
    normalized = replaceMathFunctionCalls(normalized);
    normalized = replaceGreekCharacters(normalized);
    normalized = replaceBareMathFunctions(normalized);
    normalized = replacePiConstant(normalized);
    normalized = replaceIdentifierSubscripts(normalized);
    normalized = romanizeWordPhrases(normalized);
    normalized = normalized
      .replace(/×/g, " \\times ")
      .replace(/÷/g, " \\div ")
      .replace(/−/g, " - ")
      .replace(/\*/g, " \\times ")
      .replace(/\s*=\s*/g, " = ")
      .replace(/\s*\+\s*/g, " + ")
      .replace(/\s*-\s*/g, " - ")
      .replace(/\s*\/\s*/g, " / ")
      .replace(/\s+/g, " ")
      .trim();
    return normalized;
  }

  function isLikelyInlineEquation(text) {
    const normalized = decodeLiteralUnicodeEscapes(text).replace(/\s+/g, " ").trim();
    if (!normalized || !normalized.includes("=") || normalized.length > 160) {
      return false;
    }
    if (
      (normalized.match(/=/g) || []).length > 1
      || /^(?:[A-Za-z][A-Za-z0-9]*(?:\s+[A-Za-z][A-Za-z0-9]*){0,5}|\d+\s*[A-Za-zµμΩ]+)\s*=\s*[-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:\s*(?:[eE]\s*[+\-−]?\d+|×\s*10(?:\^[+\-−]?\d+|[⁻⁺⁰¹²³⁴⁵⁶⁷⁸⁹]+)))?(?:\s*[A-Za-zµμΩ%°][A-Za-z0-9µμΩ%°·./^+\-]*)?$/.test(normalized)
    ) {
      return false;
    }
    return (
      /[0-9]/.test(normalized)
      || /[_+\-*/^()]/.test(normalized)
      || /\b(?:sqrt|sin|cos|tan|asin|acos|atan|ln|log10|log|exp|abs|radians|degrees)\b/i.test(normalized)
      || /[α-ωΑ-Ω]/.test(normalized)
    );
  }

  function isPotentialExcelFormulaStart(text, startIndex) {
    if ((text[startIndex] || "") !== "=") {
      return false;
    }
    const previous = text[startIndex - 1] || "";
    if (previous && !/[\s([{,;:]/.test(previous)) {
      return false;
    }
    return /\S/.test(text.slice(startIndex + 1));
  }

  function findExcelFormulaEnd(text, startIndex) {
    let index = startIndex + 1;
    let parenDepth = 0;
    let insideString = false;

    while (index < text.length) {
      const character = text[index];

      if (character === "\n") {
        break;
      }

      if (character === "\"") {
        if (insideString && text[index + 1] === "\"") {
          index += 2;
          continue;
        }
        insideString = !insideString;
        index += 1;
        continue;
      }

      if (!insideString) {
        if (character === "(") {
          parenDepth += 1;
        } else if (character === ")" && parenDepth > 0) {
          parenDepth -= 1;
        } else if (parenDepth === 0 && /[?!]/.test(character)) {
          break;
        } else if (parenDepth === 0 && character === ".") {
          const nextCharacter = text[index + 1] || "";
          if (!/\d/.test(nextCharacter)) {
            break;
          }
        } else if (parenDepth === 0 && /\s/.test(character)) {
          const boundaryMatch = /^(\s+)([A-Za-z][A-Za-z-]*)\b/.exec(text.slice(index));
          if (boundaryMatch && excelFormulaBoundaryWords.has(boundaryMatch[2].toLowerCase())) {
            break;
          }
        }
      }

      index += 1;
    }

    while (index > startIndex + 1 && /\s/.test(text[index - 1])) {
      index -= 1;
    }
    return index;
  }

  function appendExcelFormula(target, formulaText) {
    const formula = document.createElement("code");
    formula.className = "preview-inline-excel-formula";
    formula.textContent = decodeLiteralUnicodeEscapes(formulaText).trim();
    target.appendChild(formula);
  }

  function appendStandardMathAwarePlainText(target, text) {
    const sourceText = decodeLiteralUnicodeEscapes(text);
    const equationPattern = new RegExp(inlineEquationPatternSource, "g");
    let lastIndex = 0;
    let match;

    while ((match = equationPattern.exec(sourceText))) {
      const plainPrefix = sourceText.slice(lastIndex, match.index);
      if (plainPrefix) {
        appendTextWithScientificNotation(target, plainPrefix);
      }

      const rawExpression = match[0];
      const splitExpression = splitEquationExpression(rawExpression);
      const expression = normalizeEquationExpression(splitExpression.equationText);
      if (isLikelyInlineEquation(expression)) {
        const inlineMath = document.createElement("span");
        inlineMath.className = "preview-inline-math";
        inlineMath.textContent = `\\(${convertInlineExpressionToTex(expression)}\\)`;
        target.appendChild(inlineMath);
        if (splitExpression.trailingText) {
          appendTextWithScientificNotation(target, normalizeEquationTrailingText(splitExpression.trailingText));
        }
      } else {
        appendTextWithScientificNotation(target, rawExpression);
      }
      lastIndex = match.index + rawExpression.length;
    }

    const trailing = sourceText.slice(lastIndex);
    if (trailing) {
      appendTextWithScientificNotation(target, trailing);
    }
  }

  function appendMathAwarePlainText(target, text, options = {}) {
    const renderOptions = normalizeRenderOptions(options);
    if (!renderOptions.excelMode) {
      appendStandardMathAwarePlainText(target, text);
      return;
    }

    const sourceText = decodeLiteralUnicodeEscapes(text);
    let segmentStart = 0;
    let searchIndex = 0;

    while (searchIndex < sourceText.length) {
      const equalsIndex = sourceText.indexOf("=", searchIndex);
      if (equalsIndex < 0) {
        break;
      }
      if (!isPotentialExcelFormulaStart(sourceText, equalsIndex)) {
        searchIndex = equalsIndex + 1;
        continue;
      }

      appendStandardMathAwarePlainText(target, sourceText.slice(segmentStart, equalsIndex));
      const formulaEnd = findExcelFormulaEnd(sourceText, equalsIndex);
      appendExcelFormula(target, sourceText.slice(equalsIndex, formulaEnd));
      segmentStart = formulaEnd;
      searchIndex = formulaEnd;
    }

    appendStandardMathAwarePlainText(target, sourceText.slice(segmentStart));
  }

  function appendPlainTextContent(target, text, options = {}) {
    const sourceText = String(text || "");
    let lastIndex = 0;
    const renderOptions = normalizeRenderOptions(options);

    sourceText.replace(mathDelimitedPattern, (match, offset) => {
      appendMathAwarePlainText(target, sourceText.slice(lastIndex, offset), renderOptions);
      target.appendChild(document.createTextNode(normalizeDelimitedMath(match)));
      lastIndex = offset + match.length;
      return match;
    });

    appendMathAwarePlainText(target, sourceText.slice(lastIndex), renderOptions);
  }

  function appendInlineMarkdown(target, inlineText, options = {}) {
    const sourceText = String(inlineText || "");
    const tokenPattern = /`[^`\n]+`|\*\*(?=\S)[\s\S]*?\S\*\*|\*(?=\S)[\s\S]*?\S\*/g;
    let inlineLastIndex = 0;
    const renderOptions = normalizeRenderOptions(options);

    function looksLikeMathCollision(tokenText) {
      const innerText = String(tokenText || "").slice(1, -1);
      return (
        innerText.includes("=")
        || /[0-9]/.test(innerText)
        || /[+\-*/^]/.test(innerText)
        || /\b(?:sqrt|sin|cos|tan|asin|acos|atan|ln|log10|log|exp|abs|radians|degrees)\b/i.test(innerText)
      );
    }

    function appendToken(targetNode, tokenText) {
      if (!tokenText) {
        return;
      }
      if (tokenText.startsWith("`") && tokenText.endsWith("`")) {
        const code = document.createElement("code");
        code.className = "preview-message-inline-code";
        code.textContent = tokenText.slice(1, -1);
        targetNode.appendChild(code);
        return;
      }
      if (
        tokenText.startsWith("**") && tokenText.endsWith("**")
      ) {
        const strong = document.createElement("strong");
        appendInlineMarkdown(strong, tokenText.slice(2, -2), renderOptions);
        targetNode.appendChild(strong);
        return;
      }
      if (tokenText.startsWith("*") && tokenText.endsWith("*")) {
        if (looksLikeMathCollision(tokenText)) {
          appendPlainTextContent(targetNode, tokenText, renderOptions);
          return;
        }
        const emphasis = document.createElement("em");
        appendInlineMarkdown(emphasis, tokenText.slice(1, -1), renderOptions);
        targetNode.appendChild(emphasis);
        return;
      }
      appendPlainTextContent(targetNode, tokenText, renderOptions);
    }

    sourceText.replace(tokenPattern, (match, offset) => {
      const plainText = sourceText.slice(inlineLastIndex, offset);
      if (plainText) {
        appendPlainTextContent(target, plainText, renderOptions);
      }
      appendToken(target, match);
      inlineLastIndex = offset + match.length;
      return match;
    });

    const trailingText = sourceText.slice(inlineLastIndex);
    if (trailingText) {
      appendPlainTextContent(target, trailingText, renderOptions);
    }
  }

  function appendListItemContent(item, itemText, options = {}) {
    const normalized = String(itemText || "").replace(/^\n+|\n+$/g, "");
    if (!normalized) {
      return;
    }
    if (/\n/.test(normalized)) {
      appendFormattedMessageContent(item, normalized, options);
      return;
    }
    appendInlineMarkdown(item, normalized, options);
  }

  function appendStructuredPlainText(container, text, options = {}) {
    const unorderedListPattern = /^\s*[-*]\s+/;
    const orderedListPattern = /^\s*\d+\.\s+/;
    const normalized = String(text || "").replace(/^\n+|\n+$/g, "");
    if (!normalized) {
      return false;
    }

    const lines = normalized.split("\n");
    const paragraphLines = [];
    let activeListType = "";
    let activeListItems = [];
    let appendedAny = false;

    function flushParagraph() {
      if (!paragraphLines.length) {
        return false;
      }
      appendTextBlock(container, paragraphLines.join("\n").trim(), options);
      paragraphLines.length = 0;
      appendedAny = true;
      return true;
    }

    function flushList() {
      if (!activeListType || !activeListItems.length) {
        return false;
      }
      const list = document.createElement(activeListType === "ordered" ? "ol" : "ul");
      list.className = "preview-message-list";
      activeListItems.forEach((itemText) => {
        const item = document.createElement("li");
        item.className = "preview-message-list-item";
        appendListItemContent(item, itemText, options);
        list.appendChild(item);
      });
      container.appendChild(list);
      activeListType = "";
      activeListItems = [];
      appendedAny = true;
      return true;
    }

    function currentListItemAppend(lineText) {
      if (!activeListItems.length) {
        return;
      }
      const lastItemIndex = activeListItems.length - 1;
      activeListItems[lastItemIndex] = `${activeListItems[lastItemIndex]}\n${lineText}`;
    }

    lines.forEach((line) => {
      const trimmed = line.trim();
      const isUnorderedListItem = unorderedListPattern.test(line);
      const isOrderedListItem = !isUnorderedListItem && orderedListPattern.test(line);
      const isStandaloneMathLine = Boolean(
        trimmed && (trimmed.startsWith("\\[") || trimmed.startsWith("\\(") || looksLikeStandaloneLatexMathBlock(trimmed)),
      );

      if (isUnorderedListItem || isOrderedListItem) {
        flushParagraph();
        const nextListType = isOrderedListItem ? "ordered" : "unordered";
        if (activeListType && activeListType !== nextListType) {
          flushList();
        }
        activeListType = nextListType;
        activeListItems.push(line.replace(isOrderedListItem ? orderedListPattern : unorderedListPattern, "").trim());
        return;
      }

      if (activeListType) {
        if (!trimmed) {
          currentListItemAppend("");
          return;
        }
        if (/^\s+/.test(line) || trimmed.startsWith("\\[") || trimmed.startsWith("\\(") || looksLikeStandaloneLatexMathBlock(trimmed)) {
          currentListItemAppend(trimmed);
          return;
        }
        flushList();
      }

      if (!trimmed) {
        flushParagraph();
        return;
      }
      if (isStandaloneMathLine) {
        flushParagraph();
        appendTextBlock(container, trimmed, options);
        appendedAny = true;
        return;
      }
      paragraphLines.push(line);
    });

    flushList();
    flushParagraph();
    return appendedAny;
  }

  function appendTextBlock(container, blockText, options = {}) {
    const normalized = decodeLiteralUnicodeEscapes(blockText).trim();
    if (
      normalized.startsWith("\\[")
      || normalized.startsWith("\\(")
      || looksLikeStandaloneLatexMathBlock(normalized)
    ) {
      const paragraph = document.createElement("p");
      paragraph.className = "preview-message-paragraph";
      paragraph.textContent = normalizeStandaloneMathBlockText(normalized);
      container.appendChild(paragraph);
      return;
    }

    const paragraph = document.createElement("p");
    paragraph.className = "preview-message-paragraph";
    appendInlineMarkdown(paragraph, blockText, options);
    container.appendChild(paragraph);
  }

  function normalizeStandaloneMathParagraphs(container) {
    if (!container) {
      return;
    }
    container.querySelectorAll("p.preview-message-paragraph").forEach((paragraph) => {
      if (!(paragraph instanceof HTMLElement) || paragraph.childElementCount) {
        return;
      }
      const text = String(paragraph.textContent || "").trim();
      if (!looksLikeStandaloneLatexMathBlock(text)) {
        return;
      }
      paragraph.textContent = normalizeStandaloneMathBlockText(text);
    });
  }

  function appendFormattedMessageContent(container, text, options = {}) {
    if (!container) {
      return;
    }

    const source = normalizeNestedDisplayMathWrappers(String(text || ""));
    const renderOptions = normalizeRenderOptions(options);
    const fencePattern = /```([\w+-]+)?\n?([\s\S]*?)```/g;
    let lastIndex = 0;
    let hasContent = false;

    function appendPlainBlocks(segmentText) {
      if (appendStructuredPlainText(container, segmentText, renderOptions)) {
        hasContent = true;
      }
    }

    function appendTextSegment(segment) {
      const normalized = String(segment || "").replace(/^\n+|\n+$/g, "");
      if (!normalized) {
        return;
      }
      appendPlainBlocks(normalized);
    }

    source.replace(fencePattern, (match, language, code, offset) => {
      appendTextSegment(source.slice(lastIndex, offset));

      const pre = document.createElement("pre");
      pre.className = "preview-message-code-block";
      if (language) {
        pre.dataset.language = String(language).trim().toLowerCase();
      }
      const codeElement = document.createElement("code");
      codeElement.className = "preview-message-code";
      codeElement.textContent = String(code || "").replace(/^\n+|\n+$/g, "");
      pre.appendChild(codeElement);
      container.appendChild(pre);
      hasContent = true;
      lastIndex = offset + match.length;
      return match;
    });

    appendTextSegment(source.slice(lastIndex));

    if (!hasContent) {
      const paragraph = document.createElement("p");
      paragraph.className = "preview-message-paragraph";
      appendInlineMarkdown(paragraph, source, renderOptions);
      container.appendChild(paragraph);
    }

    normalizeStandaloneMathParagraphs(container);
    renderMath(container);
  }

  function appendInlineText(target, text, options = {}) {
    if (!target) {
      return;
    }
    target.textContent = "";
    appendInlineMarkdown(target, text, options);
    renderMath(target);
  }

  function buildTextPanel(headingText, bodyText, extraClass = "", options = {}) {
    const panel = document.createElement("div");
    panel.className = `preview-written-answer-panel${extraClass ? ` ${extraClass}` : ""}`;
    const heading = document.createElement("span");
    heading.className = "preview-written-answer-heading";
    heading.textContent = headingText;
    panel.appendChild(heading);
    appendFormattedMessageContent(panel, bodyText || "No answer submitted.", options);
    return panel;
  }

  window.StandaloneRichText = {
    appendFormattedMessageContent,
    appendInlineText,
    buildTextPanel,
    renderMath,
  };
}());
