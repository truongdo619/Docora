import React, {
  CSSProperties,
  MouseEvent,
  useState,
} from "react";
import "../style/TextHighlight.css";
import type { ViewportHighlight } from "../types";
import Badge from "@mui/material/Badge";

/* --------------------------------------------------------------------- */
/*  TOY DATA – remove or replace with real annotations later             */
/* --------------------------------------------------------------------- */
export interface ImplicitEntity {
  mention: string;    // surface form
  resolved: string;   // canonical entity
  type?: string;      // optional label (MATERIAL, ABBR, …)
}

export const TOY_IMPLICIT_ENTITIES: ImplicitEntity[] = [
  {
    mention: "it",
    resolved: "Sulfonated polyarylenethioethersulfone",
    type: "MATERIAL",
  },
  {
    mention: "this polymer",
    resolved: "Sulfonated polyarylenethioethersulfone",
    type: "MATERIAL",
  },
  {
    mention: "SPAES",
    resolved: "Sulfonated polyarylenethioethersulfone",
    type: "ABBR",
  },
  {
    mention: "its membrane",
    resolved: "Sulfonated polyarylenethioethersulfone membrane",
    type: "PART",
  },
];
/* --------------------------------------------------------------------- */

export interface TextHighlightProps {
  highlight: ViewportHighlight & {
    implicitEntities?: ImplicitEntity[];   // optional field
  };
  onClick?(event: MouseEvent<HTMLDivElement>): void;
  onMouseOver?(event: MouseEvent<HTMLDivElement>): void;
  onMouseOut?(event: MouseEvent<HTMLDivElement>): void;
  isScrolledTo: boolean;
  onContextMenu?(event: MouseEvent<HTMLDivElement>): void;
  style?: CSSProperties;
}

export const TextHighlight = ({
  highlight,
  onClick,
  onMouseOver,
  onMouseOut,
  isScrolledTo,
  onContextMenu,
  style,
}: TextHighlightProps) => {
  /* dialog state */

  /* helpers */
  const highlightClass = isScrolledTo ? "TextHighlight--scrolledTo" : "";
  const { rects } = highlight.position;
  const classnametext = highlight.comment.toUpperCase();
  const para_id = highlight.para_id;

  /* view */
  return (
    <div
      className={`TextHighlight ${highlightClass}`}
      onContextMenu={onContextMenu}
    >
      <div className="TextHighlight__parts">
        {rects.map((rect, index) => (
          <div
            key={index}
            onMouseOver={onMouseOver}
            onMouseOut={onMouseOut}
            onClick={onClick}
            style={{ ...rect, ...style, position: "absolute" }}
            className={`TextHighlight__part ${classnametext}`}
          >
            {/* paragraph number badge */}
            {classnametext.startsWith("BLOCK") &&
              index === 0 &&
              para_id !== undefined && (
                <Badge
                  badgeContent={para_id + 1}
                  color="primary"
                  sx={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    color: "white",
                  }}
                  showZero
                  max={999}
                />
              )}

          </div>
        ))}
      </div>

    </div>
  );
};
