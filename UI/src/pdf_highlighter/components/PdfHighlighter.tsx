import "pdfjs-dist/web/pdf_viewer.css";
import "../style/PdfHighlighter.css";
import "../style/pdf_viewer.css";
import CommentForm from "./CommentForm";
import debounce from "lodash.debounce";
import { PDFDocumentProxy } from "pdfjs-dist";
import { CommentedHighlight } from "../types";
import { GlobalContext } from '../../GlobalState';
import {
  EventBus,
  NullL10n,
  PDFLinkService,
  PDFViewer,
} from "pdfjs-dist/legacy/web/pdf_viewer";
import React, {
  CSSProperties,
  PointerEventHandler,
  ReactNode,
  useLayoutEffect,
  useRef,
  useState,
  useContext
} from "react";
import { createRoot } from "react-dom/client";
import {
  PdfHighlighterContext,
  PdfHighlighterUtils,
} from "../contexts/PdfHighlighterContext";
import { scaledToViewport, viewportPositionToScaled } from "../lib/coordinates";
import { disableTextSelection } from "../lib/disable-text-selection";
import getBoundingRect from "../lib/get-bounding-rect";
import getClientRects from "../lib/get-client-rects";
import groupHighlightsByPage from "../lib/group-highlights-by-page";
import {
  asElement,
  findOrCreateContainerLayer,
  getPagesFromRange,
  getWindow,
  isHTMLElement,
} from "../lib/pdfjs-dom";
import {
  Content,
  GhostHighlight,
  Highlight,
  HighlightBindings,
  PdfScaleValue,
  PdfSelection,
  Tip,
  ViewportPosition,
} from "../types";
import { HighlightLayer } from "./HighlightLayer";
import { MouseSelection } from "./MouseSelection";
import { TipContainer } from "./TipContainer";
import TreeVisualizationExample from './TreeVisualizationExample';

// Material UI dialog imports
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import Button from '@mui/material/Button';

const SCROLL_MARGIN = 10;
const SELECTION_DELAY = 250; // Debounce wait time in milliseconds for a selection changing to be registered
const DEFAULT_SCALE_VALUE = "auto";
const DEFAULT_TEXT_SELECTION_COLOR = "rgba(153,193,218,255)";

const findOrCreateHighlightLayer = (textLayer: HTMLElement) => {
  return findOrCreateContainerLayer(
    textLayer,
    "PdfHighlighter__highlight-layer",
  );
};

/**
 * The props type for {@link PdfHighlighter}.
 *
 * @category Component Properties
 */
export interface PdfHighlighterProps {
  /**
   * Array of all highlights to be organised and fed through to the child
   * highlight container.
   */
  highlights: Array<Highlight>;

  /**
   * Event is called only once whenever the user changes scroll after
   * the autoscroll function, scrollToHighlight, has been called.
   */
  onScrollAway?(): void;

  /**
   * What scale to render the PDF at inside the viewer.
   */
  pdfScaleValue?: PdfScaleValue;

  /**
   * Callback triggered whenever a user finishes making a mouse selection or has
   * selected text.
   *
   * @param PdfSelection - Content and positioning of the selection. NOTE:
   * `makeGhostHighlight` will not work if the selection disappears.
   */
  onSelection?(PdfSelection: PdfSelection): void;

  /**
   * Callback triggered whenever a ghost (non-permanent) highlight is created.
   *
   * @param ghostHighlight - Ghost Highlight that has been created.
   */
  onCreateGhostHighlight?(ghostHighlight: GhostHighlight): void;

  /**
   * Callback triggered whenever a ghost (non-permanent) highlight is removed.
   *
   * @param ghostHighlight - Ghost Highlight that has been removed.
   */
  onRemoveGhostHighlight?(ghostHighlight: GhostHighlight): void;

  /**
   * Optional element that can be displayed as a tip whenever a user makes a
   * selection.
   */
  selectionTip?: ReactNode;

  /**
   * Condition to check before any mouse selection starts.
   *
   * @param event - mouse event associated with the new selection.
   * @returns - `True` if mouse selection should start.
   */
  enableAreaSelection?(event: MouseEvent): boolean;

  /**
   * Optional CSS styling for the rectangular mouse selection.
   */
  mouseSelectionStyle?: CSSProperties;

  /**
   * PDF document to view and overlay highlights.
   */
  pdfDocument: PDFDocumentProxy;

  /**
   * This should be a highlight container/renderer of some sorts. It will be
   * given appropriate context for a single highlight which it can then use to
   * render a TextHighlight, AreaHighlight, etc. in the correct place.
   */
  children: ReactNode;

  /**
   * Coloring for unhighlighted, selected text.
   */
  textSelectionColor?: string;

  /**
   * Creates a reference to the PdfHighlighterContext above the component.
   *
   * @param pdfHighlighterUtils - various useful tools with a PdfHighlighter.
   * See {@link PdfHighlighterContext} for more description.
   */
  utilsRef(pdfHighlighterUtils: PdfHighlighterUtils): void;

  /**
   * Style properties for the PdfHighlighter (scrollbar, background, etc.), NOT
   * the PDF.js viewer it encloses. If you want to edit the latter, use the
   * other style props like `textSelectionColor` or overwrite pdf_viewer.css
   */
  style?: CSSProperties;

  /**
   * Callback to be invoked when the current page changes.
   */
  onPageChange?: (page: number) => void;
}

/**
 * This is a large-scale PDF viewer component designed to facilitate
 * highlighting. It should be used as a child to a {@link PdfLoader} to ensure
 * proper document loading. This does not itself render any highlights, but
 * instead its child should be the container component for each individual
 * highlight. This component will be provided appropriate HighlightContext for
 * rendering.
 *
 * @category Component
 */
export const PdfHighlighter = ({
  highlights,
  onScrollAway,
  pdfScaleValue = DEFAULT_SCALE_VALUE,
  onSelection: onSelectionFinished,
  onCreateGhostHighlight,
  onRemoveGhostHighlight,
  selectionTip,
  enableAreaSelection,
  mouseSelectionStyle,
  pdfDocument,
  children,
  textSelectionColor = DEFAULT_TEXT_SELECTION_COLOR,
  utilsRef,
  style,
  onPageChange
}: PdfHighlighterProps) => {
  // State
  const globalContext = useContext(GlobalContext);
  
  const [openTreeDialog, setOpenTreeDialog] = useState(false);
  const [treeDialogHighlightId, setTreeDialogHighlightId] = useState<string | null>(null);

  // ───────────────────────────────────────────────────────────
  //  NEW — comment‑editing dialog state & helpers
  // ───────────────────────────────────────────────────────────
  const [commentDialogData, setCommentDialogData] = useState<{
    highlight: Highlight;
    brat_item: any;
  } | null>(null);
  
  const handleCloseCommentDialog = () => {
    setCommentDialogData(null);
    toggleEditInProgress(false);
  };

  const handleOpenTreeDialog = (id: string) => {
    setTreeDialogHighlightId(id);
    setOpenTreeDialog(true);
  };
  
  const handleCloseTreeDialog = () => {
    const hash = document.location.hash;
    const parts = hash.split('#');
    document.location.hash = parts[0] + "#" + parts[1];
    setOpenTreeDialog(false);
  };


  // const location = useLocation();
  // const brat_output = location.state?.brat_output || [];
  if (!globalContext) {
    throw new Error("GlobalContext is undefined");
  }
  const { bratOutput } = globalContext;

  // const [bratOutput, setBratOutput] = useState<Array<[]>>(
  //   brat_output ?? [],
  // );

  const [tip, setTip] = useState<Tip | null>(null);
  const [isViewerReady, setIsViewerReady] = useState(false);

  // Refs
  const containerNodeRef = useRef<HTMLDivElement | null>(null);
  const highlightBindingsRef = useRef<{ [page: number]: HighlightBindings }>(
    {},
  );
  const ghostHighlightRef = useRef<GhostHighlight | null>(null);
  const selectionRef = useRef<PdfSelection | null>(null);
  const scrolledToHighlightIdRef = useRef<string | null>(null);
  const isAreaSelectionInProgressRef = useRef(false);
  const isEditInProgressRef = useRef(false);
  const updateTipPositionRef = useRef(() => {});

  const eventBusRef = useRef<EventBus>(new EventBus());
  const linkServiceRef = useRef<PDFLinkService>(
    new PDFLinkService({
      eventBus: eventBusRef.current,
      externalLinkTarget: 2,
    }),
  );
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const viewerRef = useRef<PDFViewer | null>(null);

  // Initialise PDF Viewer
  useLayoutEffect(() => {
    if (!containerNodeRef.current) return;

    const debouncedDocumentInit = debounce(() => {
      viewerRef.current =
        viewerRef.current ||
        new PDFViewer({
          container: containerNodeRef.current!,
          eventBus: eventBusRef.current,
          // @ts-ignore enhanceTextSelection is deprecated but this is the last version to support it. See: https://github.com/DanielArnould/react-pdf-highlighter-extended/issues/3
          enhanceTextSelection: true,
          textLayerMode: 2,
          removePageBorders: true,
          linkService: linkServiceRef.current,
          l10n: NullL10n, // No localisation
        });

      viewerRef.current.setDocument(pdfDocument);
      linkServiceRef.current.setDocument(pdfDocument);
      linkServiceRef.current.setViewer(viewerRef.current);
      setIsViewerReady(true);
    }, 100);

    debouncedDocumentInit();

    return () => {
      debouncedDocumentInit.cancel();
    };
  }, [document]);

  // Initialise viewer event listeners
  useLayoutEffect(() => {

    // console.log("pphighlights", highlights);
    if (!containerNodeRef.current) return;

    resizeObserverRef.current = new ResizeObserver(handleScaleValue);
    resizeObserverRef.current.observe(containerNodeRef.current);

    const doc = containerNodeRef.current.ownerDocument;

    eventBusRef.current.on("textlayerrendered", renderHighlightLayers);
    eventBusRef.current.on("pagesinit", handleScaleValue);
    eventBusRef.current.on("pagechanging", handlePageChange);
    doc.addEventListener("selectionchange", debouncedHandleSelectionChange);
    doc.addEventListener("keydown", handleKeyDown);
    doc.addEventListener("mousedown", handleMouseDownWrapper, true);

    renderHighlightLayers();

    return () => {
      eventBusRef.current.off("pagesinit", handleScaleValue);
      eventBusRef.current.off("textlayerrendered", renderHighlightLayers);
      eventBusRef.current.off("pagechanging", handlePageChange);
      doc.removeEventListener(
        "selectionchange",
        debouncedHandleSelectionChange,
      );
      doc.removeEventListener("keydown", handleKeyDown);
      doc.removeEventListener("mousedown", handleMouseDownWrapper, true);
      resizeObserverRef.current?.disconnect();
    };
  }, [selectionTip, highlights, onSelectionFinished]);

  // Event listeners
  const handleScroll = () => {
    onScrollAway && onScrollAway();
    scrolledToHighlightIdRef.current = null;
    // renderHighlightLayers();
  };

  const debouncedHandleSelectionChange = debounce(() => {
    const container = containerNodeRef.current;
    const selection = getWindow(container).getSelection();

    if (!container || !selection || selection.isCollapsed || !viewerRef.current)
      return;

    const range = selection.rangeCount > 0 ? selection.getRangeAt(0) : null;

    // Check the selected text is in the document, not the tip
    if (!range || !container.contains(range.commonAncestorContainer)) return;

    const pages = getPagesFromRange(range);
    if (!pages || pages.length === 0) return;

    const rects = getClientRects(range, pages);
    if (rects.length === 0) return;

    const viewportPosition: ViewportPosition = {
      boundingRect: getBoundingRect(rects),
      rects,
    };

    const scaledPosition = viewportPositionToScaled(
      viewportPosition,
      viewerRef.current,
    );

    const content: Content = {
      text: selection.toString().split("\n").join(" "), // Make all line breaks spaces
    };

    selectionRef.current = {
      content,
      position: scaledPosition,
      makeGhostHighlight: () => {
        ghostHighlightRef.current = {
          content: content,
          position: scaledPosition,
        };

        onCreateGhostHighlight &&
          onCreateGhostHighlight(ghostHighlightRef.current);
        clearTextSelection();
        renderHighlightLayers();
        return ghostHighlightRef.current;
      },
    };

    onSelectionFinished && onSelectionFinished(selectionRef.current);

    selectionTip &&
      setTip({ position: viewportPosition, content: selectionTip });
  }, SELECTION_DELAY);

  const handleMouseDown: PointerEventHandler<HTMLDivElement> = (event) => {
    if (
      !isHTMLElement(event.target) ||
      asElement(event.target).closest(".PdfHighlighter__tip-container")
    ) {
      return;
    }

    // Check if the click is on the scrollbar
    if (event.target === containerNodeRef.current) {
      const { clientX, clientY } = event;
      if (!containerNodeRef.current) return;
      const { offsetWidth, offsetHeight, clientWidth, clientHeight } = containerNodeRef.current;
      if (
        clientX > offsetWidth - clientWidth ||
        clientY > offsetHeight - clientHeight
      ) {
        return; // Click was on the scrollbar, do not close the CommentForm
      }
    }

    setTip(null);
    clearTextSelection(); // TODO: Check if clearing text selection only if not clicking on tip breaks anything.
    removeGhostHighlight();
    toggleEditInProgress(false);
  };
  
  const handleMouseDownWrapper = (event: MouseEvent) => { 
    handleMouseDown(event as unknown as React.PointerEvent<HTMLDivElement>);
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.code === "Escape") {
      clearTextSelection();
      removeGhostHighlight();
      setTip(null);
    }
  };

  const handleScaleValue = () => {
    if (viewerRef.current) {
      viewerRef.current.currentScaleValue = pdfScaleValue.toString();
    }
  };

  const handlePageChange = (event: any) => {
    const currentPage = event.pageNumber;
    if (onPageChange) onPageChange(currentPage);
  };

  // Render Highlight layers
  const renderHighlightLayer = (
    highlightBindings: HighlightBindings,
    pageNumber: number,
  ) => {
    if (!viewerRef.current) return;

    highlightBindings.reactRoot.render(
      <PdfHighlighterContext.Provider value={pdfHighlighterUtils}>
        <HighlightLayer
          highlightsByPage={groupHighlightsByPage([
            ...highlights,
            ghostHighlightRef.current,
          ])}
          pageNumber={pageNumber}
          scrolledToHighlightId={scrolledToHighlightIdRef.current}
          viewer={viewerRef.current}
          highlightBindings={highlightBindings}
          children={children}
        />
      </PdfHighlighterContext.Provider>,
    );
  };

  const renderHighlightLayers = () => {
    if (!viewerRef.current) return;
    for (let pageNumber = 1; pageNumber <= pdfDocument.numPages; pageNumber++) {
      const highlightBindings = highlightBindingsRef.current[pageNumber];

      // Need to check if container is still attached to the DOM as PDF.js can unload pages.
      if (highlightBindings?.container?.isConnected) {
        // console.log(highlightBindings, pageNumber);
        renderHighlightLayer(highlightBindings, pageNumber);
      } else {
        const { textLayer } =
          viewerRef.current!.getPageView(pageNumber - 1) || {};
        if (!textLayer) continue; // Viewer hasn't rendered page yet

        // textLayer.div for version >=3.0 and textLayer.textLayerDiv otherwise.
        const highlightLayer = findOrCreateHighlightLayer(
          textLayer.textLayerDiv,
        );

        if (highlightLayer) {
          
          const reactRoot = createRoot(highlightLayer);
          highlightBindingsRef.current[pageNumber] = {
            reactRoot,
            container: highlightLayer,
            textLayer: textLayer.textLayerDiv, // textLayer.div for version >=3.0 and textLayer.textLayerDiv otherwise.
          };

          renderHighlightLayer(
            highlightBindingsRef.current[pageNumber],
            pageNumber,
          );
        }
      }
    }
  };

  // Utils
  const isEditingOrHighlighting = () => {
    return (
      Boolean(selectionRef.current) ||
      Boolean(ghostHighlightRef.current) ||
      isAreaSelectionInProgressRef.current ||
      isEditInProgressRef.current
    );
  };

  const toggleEditInProgress = (flag?: boolean) => {
    if (flag !== undefined) {
      isEditInProgressRef.current = flag;
    } else {
      isEditInProgressRef.current = !isEditInProgressRef.current;
    }

    // Disable text selection
    if (viewerRef.current)
      viewerRef.current.viewer?.classList.toggle(
        "PdfHighlighter--disable-selection",
        isEditInProgressRef.current,
      );
  };

  const removeGhostHighlight = () => {
    if (onRemoveGhostHighlight && ghostHighlightRef.current)
      onRemoveGhostHighlight(ghostHighlightRef.current);
    ghostHighlightRef.current = null;
    renderHighlightLayers();
  };

  const clearTextSelection = () => {
    selectionRef.current = null;

    const container = containerNodeRef.current;
    const selection = getWindow(container).getSelection();
    if (!container || !selection) return;
    selection.removeAllRanges();
  };

  const custom_scrollToHighlight = (highlight: Highlight, editHighlight: (idToUpdate: string, edit: Partial<CommentedHighlight>)=> void, selectedMode: String) => {
    const { boundingRect, usePdfCoordinates } = highlight.position;
    const pageNumber = boundingRect.pageNumber;

    // Remove scroll listener in case user auto-scrolls in succession.
    viewerRef.current!.container.removeEventListener("scroll", handleScroll);

    const pageViewport = viewerRef.current!.getPageView(
      pageNumber - 1,
    ).viewport;
    // console.log("log from custom pdfhightlighter")
    // console.log(pageViewport);
    // console.log(scaledToViewport(boundingRect, pageViewport, usePdfCoordinates))
    // console.log(...pageViewport.convertToPdfPoint(
    //   0, // Default x coord
    //   scaledToViewport(boundingRect, pageViewport, usePdfCoordinates).top -
    //     SCROLL_MARGIN,
    // ));
    viewerRef.current!.scrollPageIntoView({
      pageNumber,
      destArray: [
        null, // null since we pass pageNumber already as an arg
        { name: "XYZ" },
        ...pageViewport.convertToPdfPoint(
          0, // Default x coord
          scaledToViewport(boundingRect, pageViewport, usePdfCoordinates).top -
            SCROLL_MARGIN,
        ),
        0, // Default z coord
      ],
    });
    let viewport = scaledToViewport(boundingRect, pageViewport, usePdfCoordinates);
    // viewport.
    
    let brat_item = undefined;
    if (selectedMode == "Events") {
      let org_brat_item = highlight.para_id !== undefined ? bratOutput[highlight.para_id] : undefined;
      brat_item = {
        text: org_brat_item?.text,
        entities: org_brat_item?.events_info.entities,
        triggers: org_brat_item?.events_info.triggers,
        events: org_brat_item?.events_info.events
      }
      

      // console.log("brat_item", brat_item);

    }
    else {
      brat_item = highlight.para_id !== undefined ? bratOutput[highlight.para_id] : undefined
    }

    brat_item["selectedMode"] = selectedMode;

    // setTip(editCommentTip);

    // Open comment‑editing dialog instead of tip
    setCommentDialogData({ highlight, brat_item });
    
    toggleEditInProgress(true);
    scrolledToHighlightIdRef.current = highlight.id;
    renderHighlightLayers();

    // wait for scrolling to finish
    setTimeout(() => {
      viewerRef.current!.container.addEventListener("scroll", handleScroll, {
        once: true,
      });
    }, 100);
  };
  
  const scrollToHighlight = (highlight: Highlight) => {
    const { boundingRect, usePdfCoordinates } = highlight.position;
    const pageNumber = boundingRect.pageNumber;

    // Remove scroll listener in case user auto-scrolls in succession.
    viewerRef.current!.container.removeEventListener("scroll", handleScroll);

    const pageViewport = viewerRef.current!.getPageView(
      pageNumber - 1,
    ).viewport;

    viewerRef.current!.scrollPageIntoView({
      pageNumber,
      destArray: [
        null, // null since we pass pageNumber already as an arg
        { name: "XYZ" },
        ...pageViewport.convertToPdfPoint(
          0, // Default x coord
          scaledToViewport(boundingRect, pageViewport, usePdfCoordinates).top -
            SCROLL_MARGIN,
        ),
        0, // Default z coord
      ],
    });

    scrolledToHighlightIdRef.current = highlight.id;
    renderHighlightLayers();

    // wait for scrolling to finish
    setTimeout(() => {
      viewerRef.current!.container.addEventListener("scroll", handleScroll, {
        once: true,
      });
    }, 100);
  };

  const pdfHighlighterUtils: PdfHighlighterUtils = {
    isEditingOrHighlighting,
    getCurrentSelection: () => selectionRef.current,
    getGhostHighlight: () => ghostHighlightRef.current,
    removeGhostHighlight,
    toggleEditInProgress,
    isEditInProgress: () => isEditInProgressRef.current,
    isSelectionInProgress: () =>
      Boolean(selectionRef.current) || isAreaSelectionInProgressRef.current,
    custom_scrollToHighlight,
    scrollToHighlight,
    getViewer: () => viewerRef.current,
    getTip: () => tip,
    setTip,
    updateTipPosition: updateTipPositionRef.current,
    renderHighlightLayers: renderHighlightLayers, // Added to allow external components to force a re-render of the highlights
    scrolledToHighlightIdRef: scrolledToHighlightIdRef
  };

  utilsRef(pdfHighlighterUtils);

  return (
    <>
    <PdfHighlighterContext.Provider value={pdfHighlighterUtils}>
      <div
        ref={containerNodeRef}
        className="PdfHighlighter"
        onPointerDown={handleMouseDown}
        style={style}
      >
        <div className="pdfViewer" />
        <style>
          {`
          .textLayer ::selection {
            background: ${textSelectionColor};
          }
        `}
        </style>
        {isViewerReady && (
          <TipContainer
            viewer={viewerRef.current!}
            updateTipPositionRef={updateTipPositionRef}
          />
        )}
        {isViewerReady && enableAreaSelection && (
          <MouseSelection
            viewer={viewerRef.current!}
            onChange={(isVisible) =>
              (isAreaSelectionInProgressRef.current = isVisible)
            }
            enableAreaSelection={enableAreaSelection}
            style={mouseSelectionStyle}
            onDragStart={() => disableTextSelection(viewerRef.current!, true)}
            onReset={() => {
              selectionRef.current = null;
              disableTextSelection(viewerRef.current!, false);
            }}
            onSelection={(
              viewportPosition,
              scaledPosition,
              image,
              resetSelection,
            ) => {
              selectionRef.current = {
                content: { image },
                position: scaledPosition,
                makeGhostHighlight: () => {
                  ghostHighlightRef.current = {
                    position: scaledPosition,
                    content: { image },
                  };
                  onCreateGhostHighlight &&
                    onCreateGhostHighlight(ghostHighlightRef.current);
                  resetSelection();
                  renderHighlightLayers();
                  return ghostHighlightRef.current;
                },
              };

              onSelectionFinished &&
                onSelectionFinished(selectionRef.current);
              selectionTip &&
                setTip({ position: viewportPosition, content: selectionTip });
            }}
          />
        )}
      </div>
    </PdfHighlighterContext.Provider>


  
    {/* ───────────────────────────────────────────────
        NEW — Comment‑editing dialog
      ─────────────────────────────────────────────── */}
    <Dialog
      open={Boolean(commentDialogData)}
      maxWidth="lg"
      fullWidth
      onClose={handleCloseCommentDialog}
    >
      {commentDialogData && (
          <DialogContent>
            <CommentForm
              highlight={commentDialogData.highlight}
              brat_item={commentDialogData.brat_item}
              setCommentDialogData={setCommentDialogData}
              toggleEditInProgress={toggleEditInProgress}
              onSubmit={() => {
                handleCloseCommentDialog();
                renderHighlightLayers();
              }}
              pdfHighlighterUtils={pdfHighlighterUtils}
              onOpenTreeDialog={() =>
                handleOpenTreeDialog(commentDialogData.highlight.id)
              }
            />
          </DialogContent>
      )}
    </Dialog>


    <Dialog open={openTreeDialog} maxWidth="lg" fullWidth>
      <DialogTitle>Graph Visualization</DialogTitle>
      <DialogContent>
        {treeDialogHighlightId && (
          <TreeVisualizationExample highlightId={treeDialogHighlightId} />
          // <HardCodedVisExample />
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleCloseTreeDialog}>Close</Button>
      </DialogActions>
    </Dialog>
    </>
  );
};
