// pdf_highlighter/utils/injectStyles.ts

interface EntityType {
  type: string;
  bgColor: string;
}

interface RelationType {
  type: string;
  color: string;
}

interface Setting {
  entity_types: EntityType[];
  relation_types: RelationType[];
}

// Convert "POLYMER_FAMILY" -> "PolymerFamily"
function toTitleCase(str: string): string {
  return str
    .toLowerCase()
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join('');
}

export function injectDynamicCSS(setting: Setting) {
  const rules: string[] = [];

  // Entity types (e.g., POLYMER, INORGANIC)
  for (const { type, bgColor } of setting.entity_types) {
    const title = toTitleCase(type);

    rules.push(`
      .${type}, .${title} {
        background: ${bgColor};
        border-color: ${bgColor};
        color: #fff;
      }
      .${type}_COLOR, .${title}_COLOR {
        color: ${bgColor} !important;
      }
    `);
  }

  // Relation types (e.g., has_property, refers_to)
  for (const { type, color } of setting.relation_types) {
    const title = toTitleCase(type);

    rules.push(`
      .${type}_COLOR, .${title}_COLOR {
        color: ${color} !important;
        border: 2px solid gray;
        border-radius: 5px;
      }
    `);
  }

  // Inject into <head>
  const style = document.createElement('style');
  style.textContent = rules.join('\n');
  document.head.appendChild(style);
}
