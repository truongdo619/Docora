import React, { useState, useEffect } from 'react';
import '../../../public/css/style-vis.css'; // Ensure the path is correct
import {collData} from '../../../public/js/brat_config'; // Import collData
import { CommentedHighlight } from "../types";

declare global {
  interface Window {
    Util: any;
    head: any;
  }
}

interface DocData {
  text: string;
  entities: Array<[]>;
  relations: Array<[]>;
}

interface BratEmbeddingProps {
  docData: DocData;
  highlight: CommentedHighlight;
}

const BratEmbedding: React.FC<BratEmbeddingProps> = ({ docData, highlight }) => {
  const [isLoaded, setIsLoaded] = useState(true);

  useEffect(() => {
    const initializeBrat = () => {
      if (window.head && window.head.ready) {
        window.head.ready(() => {
          var dispatcher = window.Util.embed('embedding-entity-example', { ...collData }, { ...docData }, []);
          setIsLoaded(true); // Set the state to true after embedding is initialized
        });
      } else {
        var dispatcher = window.Util.embed('embedding-entity-example', { ...collData }, { ...docData }, []);
        setIsLoaded(true); // Set the state to true after embedding is initialized
      }
        
      // dispatcher.on('doneRendering', function () {      /* visualizer.js posts ‘doneRendering’ :contentReference[oaicite:2]{index=2}&#8203;:contentReference[oaicite:3]{index=3} */
      //   var $rect = $('#embedding-entity-example')
      //         .find('rect[data-span-id="' + highlight.id.split("_")[1] + '"]');
        
      //   console.log($rect);
      //   if ($rect.length) {
      //     // fire the native mouseover event – this runs the same
      //     // onMouseOver logic as a real hover
      //     $rect[0].dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
      //   }
      // });

      const PINNED = highlight.id.split("_")[1]; // Extract the ID from the highlight prop
      /* ------------------------------------------------
      * helper: reproduces the normal hover highlight
      * ---------------------------------------------- */
      function lightUp(id) {
        const r = document.querySelector(
                  `#embedding-entity-example rect[data-span-id="${id}"]`);
        if (r) {
          r.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
        }
      }
    
      /* ------------------------------------------------
      * after the SVG is ready, pin the highlight once
      * ---------------------------------------------- */
      dispatcher.on('doneRendering', () => {
        lightUp(PINNED);
      });
    
      /* ------------------------------------------------
      * every time brat removes a highlight (it does so
      * on *any* mouseout), put ours back immediately.
      * ------------------------------------------------
      * We rely on the fact that brat first clears the
      * previous highlight, then raises a fresh
      * mouseover for the span under the pointer:
      * our listener runs in between and re‑ignites
      * the pinned one, so both highlights can coexist.
      */
      $('#embedding-entity-example')
        .on('mouseout.pin', () => lightUp(PINNED));   // put back after clears
    };

    initializeBrat();
  }, [docData]);

  return (
    <div>
      {isLoaded && <b>Brat Visualization:</b>}
      <div id="embedding-entity-example"></div>
    </div>
  );
};

export default BratEmbedding;