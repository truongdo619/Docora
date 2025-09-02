import React, { useMemo, useState, useContext, useEffect } from "react";
import { GlobalContext } from "../GlobalState";

interface CommentFormProps {
  onSubmit: (input: string) => void;
  placeHolder?: string;
  defaultValue?: string; // optional: preselect a value
}

const CommentForm = ({ onSubmit, placeHolder = "Please select", defaultValue }: CommentFormProps) => {
  const global = useContext(GlobalContext);
  if (!global) throw new Error("GlobalContext must be used within a GlobalProvider");

  const { settings } = global;

  type EntityDef = { type: string; labels?: string[]; [k: string]: any };

  // Build list of entity type strings from settings
  const entityTypes = useMemo<string[]>(
    () => ((settings?.entity_types as EntityDef[] | undefined)?.map(e => e.type)) ?? [],
    [settings?.entity_types]
  );

  const [input, setInput] = useState<string>("");

  // Initialize or correct the selected value when settings load/change
  useEffect(() => {
    if (defaultValue && entityTypes.includes(defaultValue)) {
      setInput(defaultValue);
    } else if (!defaultValue && !input && entityTypes.length === 1) {
      // if only one option exists, auto-select it (optional behavior)
      setInput(entityTypes[0]);
    } else if (input && !entityTypes.includes(input)) {
      // previously selected value no longer valid → reset
      setInput("");
    }
  }, [entityTypes, defaultValue]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <form
      className="Tip__card"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(input);
      }}
    >
      <div>
        <label htmlFor="comment">Choose a label:</label>
        <select
          id="comment"
          name="comment"
          value={input}
          onChange={(event) => setInput(event.target.value)}
        >
          {/* Placeholder option */}
          <option value="" disabled>
            {placeHolder}
          </option>

          {/* Options from settings */}
          {entityTypes.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      <div>
        <input type="submit" value="Save" disabled={!input} />
      </div>
    </form>
  );
};

export default CommentForm;
