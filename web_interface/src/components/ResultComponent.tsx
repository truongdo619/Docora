import React, { MouseEvent, useEffect, useRef, useState, useContext } from "react";
import CommentForm from "./CommentForm";
import { useLocation } from 'react-router-dom';
import ContextMenu, { ContextMenuProps } from "./ContextMenu";
import ExpandableTip from "./ExpandableTip";
import HighlightContainer from "./HighlightContainer";
import Sidebar from "./Sidebar";
import ParagraphSidebar from "./ParagraphSidebar";
import SettingSidebar from "./SettingSidebar";
import EventSidebar from "./EventSidebar";
import Toolbar from "./Toolbar";
import { GlobalContext } from '../GlobalState';
import LoadingOverlay from 'react-loading-overlay-ts'; // Add this import
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../axiosSetup';
import {
  GhostHighlight,
  Highlight,
  PdfHighlighter,
  PdfHighlighterUtils,
  PdfLoader,
  Tip,
  ViewportHighlight
} from "../react-pdf-highlighter-extended";
import '../style/App.css';
import { CommentedHighlight } from "../types";
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography, Box, Divider, Tooltip } from "@mui/material";
import InfoIcon from '@mui/icons-material/Info';
import { Timeline, TimelineItem, TimelineSeparator, TimelineDot, TimelineConnector, TimelineContent } from '@mui/lab';


const getNextId = (paraId: number, entityId: number) => `para${paraId}_T${entityId}`;

const parseIdFromHash = () => {
  return document.location.hash.split("#").pop()?.slice("#highlight-".length - 1);
};

const resetHash = () => {
  const hash = document.location.hash;
  const parts = hash.split('#');
  document.location.hash = parts[0] + "#" + parts[1];
};

const extractRelationHighlights = (highlights: Array<CommentedHighlight>) => {
  const relationHighlights = highlights
    .filter(highlight => highlight.relations && highlight.relations.length > 0) // Filter highlights with relations
    .map(highlight => ({
      ...highlight,
      relationTypes: highlight.relations.map(relation => relation.type) // Extract relation types
    }));

  return relationHighlights;
};

const extractEventHighlights = (
  highlights: Array<CommentedHighlight>,
) => highlights
      .filter(h => h.trigger && h.trigger !== "none")
      .map(h => ({
        ...h,
        /*  (optional) surface the trigger if you want to display it) */
        triggerType: h.trigger,
      }));


const convertBratOutputToHighlights = (bratOutput: any[]): Highlight[] => {
  // console.log("bratOutput", bratOutput);
  let highlights: Highlight[] = [];
  bratOutput.forEach((para, paraId) => {
    const highlight: Highlight = {
      id:  `para${paraId}`,
      comment: "BLOCK_" + para.type.toUpperCase(), 
      content: {
        text: para.text,
      },      
      position: {
        boundingRect: para.bounding_box[0], 
        rects: para.bounding_box
      },
      para_id: paraId,
      visible: para.visible
    };

    highlights.push(highlight);
  });
  return highlights;
};



const ResultComponent = () => {
  const [isActive, setIsActive] = useState(false); // Add this state
  const [relationHighlights, setRelationHighlights] = useState<Array<CommentedHighlight>>([]); // Add this state
  const [eventHighlights, setEventHighlights] = useState<Array<CommentedHighlight>>([]);

  const globalContext = useContext(GlobalContext);

  if (!globalContext) {
    throw new Error("GlobalContext must be used within a GlobalProvider");
  }
  const { bratOutput, documentId, updateId, setBratOutput, setDocumentId, setUpdateId, setFileName } = globalContext;
  const navigate = useNavigate();
  const navigateTo = useNavigate();
  const paraHighlights = convertBratOutputToHighlights(bratOutput);
  // console.log("paraHighlights", paraHighlights);

  const [currentPDFPage, setCurrentPDFPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const location = useLocation();
  const initialHighlights = location.state?.highlights || [];
  const initialVisibleHighlights = initialHighlights.filter((highlight: CommentedHighlight) => highlight.visible);
  // console.log("Initial highlights", initialHighlights);
  const MAIN_URL = location.state?.url || "";
  const [url, setUrl] = useState(MAIN_URL);
  const [highlights, setHighlights] = useState<Array<CommentedHighlight>>(
    initialVisibleHighlights ?? [],
  );

  
  const setVisibleHighlights = (
    value: React.SetStateAction<Array<CommentedHighlight>>
  ) => {
    setHighlights((prev) => {
      const newHighlights = typeof value === "function" ? value(prev) : value;
      return newHighlights.filter((hl) => hl.visible);
    });
  };
  
  // useEffect(() => {
  //   setRelationHighlights(extractRelationHighlights(highlights));
  // }, [highlights]);

  // Example history events (toy data)
  const [history, setHistory] = useState<{ id: number, name: string; upload_time: string }[]>([]);

  const [filteredHighlights, setFilteredHighlights] = useState<Array<CommentedHighlight>>([]);
  const [filteredRelationHighlights, setFilteredRelationHighlights] = useState<Array<CommentedHighlight>>([]); // Add this state for relation filtering
  const [isFiltered, setIsFiltered] = useState(false);
  const [isRelationFiltered, setIsRelationFiltered] = useState(false); // Add this state for relation filtering
  const [contextMenu, setContextMenu] = useState<ContextMenuProps | null>(null);
  // Default to 1.0 scale value
  const [pdfScaleValue, setPdfScaleValue] = useState<number>(1.0);
  const [isDialogOpen, setIsDialogOpen] = useState(false); // State for dialog visibility
  const [hover, setHover] = useState(false); // State for hover

  // New state to store PDF document reference
  const [pdfDocument, setPdfDocument] = useState<PDFDocumentProxy | null>(null);

  // Refs for PdfHighlighter utilities
  const highlighterUtilsRef = useRef<PdfHighlighterUtils>();

  // State to track the last entity ID used in each paragraph
  const [lastEntityIds, setLastEntityIds] = useState<{ [key: number]: number }>({});

  // New state to track selected mode
  const [selectedMode, setSelectedMode] = useState<'Entities' | 'Relations' | 'Events' | 'Paragraphs'>('Entities');
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false);
  const [selectedHistory, setSelectedHistory] = useState<{ id: number, real_id: number, name: string; upload_time: string } | null>(null);


  // New ref for PDF container
  const pdfContainerRef = useRef<HTMLDivElement>(null);

  // Set total pages when the pdfDocument changes
  useEffect(() => {
    if (pdfDocument) {
      setTotalPages(pdfDocument.numPages);
    }
  }, [pdfDocument]);

  // Click listeners for context menu
  useEffect(() => {
    const handleClick = () => {
      if (contextMenu) {
        setContextMenu(null);
      }
    };

    document.addEventListener("click", handleClick);

    return () => {
      document.removeEventListener("click", handleClick);
    };
  }, [contextMenu]);

  // Scroll slightly when selectedMode changes
  useEffect(() => {
    // document.location.hash = "";
    // console.log("Selected mode changed to", selectedMode);
    if (highlighterUtilsRef.current) {
      highlighterUtilsRef.current.scrolledToHighlightIdRef.current = null;
      highlighterUtilsRef.current.renderHighlightLayers();
    }
    if (selectedMode === "Relations"){
      setRelationHighlights(extractRelationHighlights(highlights));
    }

    if (selectedMode === "Events"){
      // setEventHighlights 20% random of the highlights
      const randomHighlights = highlights.filter(() => Math.random() < 0.2);
      setEventHighlights(extractEventHighlights(highlights));
      // setEventHighlights(randomHighlights);
    }

  }, [selectedMode]);

  useEffect(() => {
    setRelationHighlights(extractRelationHighlights(highlights));
    // setEventHighlights(extractEventHighlights(highlights));
  }, [highlights]);

  
  const handleContextMenu = (
    event: MouseEvent<HTMLDivElement>,
    highlight: ViewportHighlight,
  ) => {
    event.preventDefault();

    // Set the context menu with position and actions
    setContextMenu({
      xPos: event.clientX,
      yPos: event.clientY,
      deleteHighlight: () => deleteHighlight(highlight),
      editComment: () => editComment(highlight), 
    });
  };

  const addHighlight = async (highlight: GhostHighlight, comment: string) => {
    const { position: { boundingRect } } = highlight;
    const paraId = findParagraphId(boundingRect);
    // console.log("Saving highlight", highlight);
    // setHighlights([{ ...highlight, comment, relations: [], para_id: paraId, id: getNextId(paraId, entityId) }, ...highlights]);
    // const text = highlight.content.text ?? '';
    // const charPositions = getCharacterPositions(paraId, text);
    setIsActive(true);
    const data = {
        document_id: documentId,
        update_id: updateId,
        para_id: paraId,
        position: highlight.position,
        comment: comment,
        scale_value: pdfScaleValue
    };
    // console.log('data:', data);
    try {
        const token = localStorage.getItem('accessToken');
        const response = await axiosInstance.post(
            `${import.meta.env.VITE_BACKEND_URL}/create-entity`,
            data,
            {
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
            }
        );

        console.log('Paragraphs updated successfully:', response.data);
        setBratOutput(response.data.brat_format_output);
        setDocumentId(response.data.document_id); // Store documentId in GlobalState
        setUpdateId(response.data.update_id);
        setVisibleHighlights(response.data.pdf_format_output);
        navigateTo('/result', { 
          state: { 
            highlights: response.data.pdf_format_output, 
            url: `${import.meta.env.VITE_PDF_BACKEND_URL}/statics/${response.data.filename}`
          }
        });
    } catch (error) {
        console.error('Error updating paragraphs:', error);
    } finally {
        setIsActive(false);
    }
  };

  // const addEntityToBratOutput = (paraId: number, entityId: number, boundingRect: any, comment: string, text: string) => {
  //   const charPositions = getCharacterPositions(paraId, text);
  //   const newEntity = [
  //     `T${entityId}`,
  //     comment,
  //     [
  //       charPositions
  //     ],
  //     text
  //   ];

  //   const updatedBratOutput = [...bratOutput];
  //   updatedBratOutput[paraId].entities.push(newEntity);
  //   setBratOutput(updatedBratOutput);
  // };

  const getCharacterPositions = (paraId: number, text: string) => {
    const paragraphText = bratOutput[paraId].text;
    const start = paragraphText.indexOf(text);
    const end = start + text.length;
    return [start, end];
  };

  const findParagraphId = (boundingRect: any) => {
    // Logic to find the paragraph ID that covers most of the bounding box
    // You need to implement this based on your specific logic
    let paraId = 0;
    // Assuming paragraphs are stored in bratOutput and have bounding boxes
    let maxOverlap = 0;
    bratOutput.forEach((para: any, index: number) => {
      const overlap = calculateOverlap(para.bounding_box, boundingRect);
      console.log(`Overlap with para ${index}: ${overlap}`);
      if (overlap > maxOverlap) {
        maxOverlap = overlap;
        paraId = index;
      }
    });
    return paraId;
  };

  const calculateOverlap = (box1: any, box2: any) => {
    const normalizedBox1 = normalizeBoundingBox(box1);
    const normalizedBox2 = normalizeBoundingBox(box2);
    const xOverlap = Math.max(0, Math.min(normalizedBox1.x2, normalizedBox2.x2) - Math.max(normalizedBox1.x1, normalizedBox2.x1));
    const yOverlap = Math.max(0, Math.min(normalizedBox1.y2, normalizedBox2.y2) - Math.max(normalizedBox1.y1, normalizedBox2.y1));
    const overlapArea = xOverlap * yOverlap;

    const box1Area = (normalizedBox1.x2 - normalizedBox1.x1) * (normalizedBox1.y2 - normalizedBox1.y1);
    const box2Area = (normalizedBox2.x2 - normalizedBox2.x1) * (normalizedBox2.y2 - normalizedBox2.y1);

    return overlapArea / Math.min(box1Area, box2Area); // Scale overlap by the smaller box area
  };

  const normalizeBoundingBox = (box: any) => {
    const { width, height } = box;
    return {
      x1: box.x1 / width,
      y1: box.y1 / height,
      x2: box.x2 / width,
      y2: box.y2 / height,
    };
  };

  const getNextEntityId = (paraId: number) => {
    const paragraph = bratOutput[paraId];
    const lastEntityId = paragraph.entities.reduce((maxId: number, entity: any) => {
      const entityId = parseInt(entity[0].substring(1));
      return Math.max(maxId, entityId);
    }, 0);
    const newEntityId = lastEntityId + 1;
    return newEntityId;
  }

  const deleteHighlight = (highlight: ViewportHighlight | Highlight) => {
    console.log("Deleting highlight", highlight);
    setVisibleHighlights(highlights.filter((h) => h.id != highlight.id));
  };

  const editHighlight = (
    idToUpdate: string,
    edit: Partial<CommentedHighlight>,
  ) => {
    console.log(`Editing highlight ${idToUpdate} with `, edit);
    setVisibleHighlights(
      highlights.map((highlight) =>
        highlight.id === idToUpdate ? { ...highlight, ...edit } : highlight,
      ),
    );
  };

  const PDFpageChange = (page: number) => {
    setCurrentPDFPage(page);
  };

  const getHighlightById = (id: string) => {
    if (selectedMode === 'Entities') {
      return highlights.find((highlight) => highlight.id === id);
    } else if (selectedMode === 'Relations') {
      return relationHighlights.find((highlight) => highlight.id === id); // Handle Relation highlights
    } else if (selectedMode === 'Events') {
      return eventHighlights.find((highlight) => highlight.id === id); // Handle Relation highlights
    } else {
      return paraHighlights.find((highlight) => highlight.id === id);
    }
  };

  const getViewportHighlightById = (id: string) => {
    let found_highlights = highlights.find((highlight) => highlight.id === id);
    let transformed = found_highlights as unknown as ViewportHighlight;
    return transformed;
  };

  // Open comment tip and update highlight with new user input
  const editComment = (highlight: ViewportHighlight<CommentedHighlight>) => {
    if (!highlighterUtilsRef.current) return;

    const editCommentTip: Tip = {
      position: highlight.position,
      content: (
        <CommentForm
          placeHolder={highlight.comment}
          onSubmit={(input) => {
            editHighlight(highlight.id, { comment: input });
            highlighterUtilsRef.current!.setTip(null);
            highlighterUtilsRef.current!.toggleEditInProgress(false);
          }}
        ></CommentForm>
      ),
    };

    highlighterUtilsRef.current.setTip(editCommentTip);
    highlighterUtilsRef.current.toggleEditInProgress(true);
  };

  // Scroll to highlight based on hash in the URL
  const scrollToHighlightFromHash = () => {
    const id = parseIdFromHash();
    
    // Check if the hash is empty
    if (id) {
      const highlight = getHighlightById(parseIdFromHash());
      // const viewport_highlight = getViewportHighlightById(parseIdFromHash());
      console.log("Highlight to scroll to", highlight);
      if (highlight && highlighterUtilsRef.current) {
        

        highlighterUtilsRef.current.custom_scrollToHighlight(highlight, editHighlight, selectedMode);
        setTimeout(() => {
          const hash = document.location.hash;
          const parts = hash.split('#');
          document.location.hash = parts[0] + "#" + parts[1] + "#highlight-" + highlight.id;
        }, 50);
      }
    }
  };

  // Hash listeners for autoscrolling to highlights
  useEffect(() => {
    window.addEventListener("hashchange", scrollToHighlightFromHash);

    return () => {
      window.removeEventListener("hashchange", scrollToHighlightFromHash);
    };
  }, [scrollToHighlightFromHash]);

  
  // // Filter highlights based on comment value
  // const filterHighlights = (comment: string) => {
  //   const filtered = highlights.filter(highlight => highlight.comment == comment);
  //   setFilteredHighlights(filtered);
  //   setIsFiltered(true);
  // };

  // // Filter highlights based on multiple comments
  // const filterHighlights = (comments: string[]) => {
  //   const filtered = highlights.filter(highlight => comments.includes(highlight.comment));
  //   setFilteredHighlights(filtered);
  //   setIsFiltered(true);
  // };


  const filterHighlights = (selectedEntityRelationMap: { [entityType: string]: string[] }) => {
    const filtered = highlights.filter(highlight => {
      const entityType = highlight.comment;
      const selectedRelationTypes = selectedEntityRelationMap[entityType];
      if (!selectedRelationTypes) return false;
      const relations = highlight.relations || [];
      if (relations.length === 0) {
        return selectedRelationTypes.includes('None');
      }
      const relationMatch = relations.some(relation => selectedRelationTypes.includes(relation.type));
      return relationMatch;
    });
    setFilteredHighlights(filtered);
    setIsFiltered(true);
  };
      

  // const filterRelations = (relationType: string) => {
  //   const filtered = relationHighlights.filter(highlight => 
  //     highlight.relationTypes.includes(relationType)
  //   );
  //   setFilteredRelationHighlights(filtered);
  //   setIsRelationFiltered(true);
  // };

  const filterRelations = (selectedRelationEntityMap: { [relationType: string]: string[] }) => {
    const filtered = relationHighlights.filter(highlight => {
      // Check if any of the highlight's relation types are in selectedRelationEntityMap
      const matchingRelationTypes = highlight.relationTypes.filter(relationType => selectedRelationEntityMap[relationType]);
  
      if (matchingRelationTypes.length === 0) return false;
  
      // Now, for each matching relation type, check if the connected entities include any of the selected entity types
      return matchingRelationTypes.some(relationType => {
        const selectedEntityTypes = selectedRelationEntityMap[relationType];
  
        // Assuming highlight has an array of connected entity types in highlight.connectedEntityTypes
        const entityType = highlight.comment || '';
  
        return selectedEntityTypes.includes(entityType);
      });
    });
  
    setFilteredRelationHighlights(filtered);
    setIsRelationFiltered(true);
  };

  // // Filter realtions based on multiple relationTypes
  // const filterRelations = (relationTypes: string[]) => {
  //   const filtered = relationHighlights.filter(highlight => {
  //     let found = false;
  //     highlight.relationTypes.forEach(relationType => {
  //       if (relationTypes.includes(relationType)) {
  //         found = true;
  //       }
  //     });
  //     return found;
  //   });
  //   setFilteredRelationHighlights(filtered);
  //   setIsRelationFiltered(true);
  // };

  const resetFilter = () => {
    setFilteredHighlights([]);
    setIsFiltered(false);
  };

  const resetRelationFilter = () => {
    setFilteredRelationHighlights([]);
    setIsRelationFiltered(false);
  };

  // Toggle dialog visibility
  const toggleDialog = async () => {
    if (!isDialogOpen) {
      try {
        const token = localStorage.getItem('accessToken');
        const response = await axiosInstance.get(
          `${import.meta.env.VITE_BACKEND_URL}/get-update-history/${documentId}`,
          {
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
            },
          }
        );
        setHistory(response.data.updates);
      } catch (error) {
        console.error('Error fetching update history:', error);
      }
    }
    setIsDialogOpen(!isDialogOpen);
  };

  // Function to handle item click and show confirm dialog
  const handleHistoryClick = (event: MouseEvent, historyItem: { id: number, real_id: number, name: string; upload_time: string }) => {
    setSelectedHistory(historyItem);
    setIsConfirmDialogOpen(true);
  };

  // Function to confirm revert
  const handleRevertConfirm = async () => {
    if (selectedHistory) {
      // console.log(`Reverting to history checkpoint: ${selectedHistory.name}`);
      // Add logic to handle revert
        setIsActive(true);
        let token = localStorage.getItem('accessToken');
    
        try {
          const response = await axiosInstance.get(
            `${import.meta.env.VITE_BACKEND_URL}/get-document/${documentId}/${selectedHistory.real_id}`,
            {
              headers: {
                'Authorization': `Bearer ${token}`,
              },
            }
          );
          setIsActive(false);
          setBratOutput(response.data.brat_format_output);
          setDocumentId(response.data.document_id);
          setUpdateId(response.data.update_id);
          setFileName(response.data.filename);
          setVisibleHighlights(response.data.pdf_format_output);
        } catch (error: any) {
          console.error('Error fetching document:', error);
          setIsActive(false);
        }
    }
    setIsConfirmDialogOpen(false);
    setIsDialogOpen(false);
  };


  // Set PdfLoader based on the selected model
  let pdfloader;
  let sidebar;
  if (selectedMode === 'Entities') {
    pdfloader = <PdfLoader document={url}>
      {(loadedPdfDocument) => {
        // Set the loaded PDF document state here
        setPdfDocument(loadedPdfDocument);
        return (
            <PdfHighlighter
              enableAreaSelection={(event) => event.altKey}
              pdfDocument={loadedPdfDocument}
              // onScrollAway={resetHash}
              utilsRef={(_pdfHighlighterUtils) => {
                highlighterUtilsRef.current = _pdfHighlighterUtils;
              }}
              pdfScaleValue={pdfScaleValue}
              selectionTip={<ExpandableTip addHighlight={(highlight, comment) => addHighlight(highlight, comment)} />}
              highlights={isFiltered ? filteredHighlights : highlights}
              style={{
                height: "calc(100% - 41px)",
              }}
              onPageChange={(page) => PDFpageChange(page)}
            >
              <HighlightContainer
                editHighlight={editHighlight}
                onContextMenu={handleContextMenu}
              />
            </PdfHighlighter>
        );
      }}
    </PdfLoader>

    sidebar = <Sidebar
        highlights={isFiltered ? filteredHighlights : highlights}
        getHighlightById={getHighlightById}
        setIsActive={setIsActive}
        setHighlights={setVisibleHighlights}
        selectedMode={selectedMode}
        paraHighlights={paraHighlights}
      />

    } else if (selectedMode === 'Relations') {
      pdfloader = (
        <PdfLoader document={url}>
          {(loadedPdfDocument) => {
            setPdfDocument(loadedPdfDocument);
            return (
              <PdfHighlighter
                enableAreaSelection={(event) => event.altKey}
                pdfDocument={loadedPdfDocument}
                utilsRef={(_pdfHighlighterUtils) => {
                  highlighterUtilsRef.current = _pdfHighlighterUtils;
                }}
                pdfScaleValue={pdfScaleValue}
                highlights={isRelationFiltered ? filteredRelationHighlights : relationHighlights}
                style={{ height: "calc(100% - 41px)" }}
                onPageChange={PDFpageChange}
              >
                <HighlightContainer editHighlight={editHighlight} onContextMenu={handleContextMenu} />
              </PdfHighlighter>
            );
          }}
        </PdfLoader>
      );
      sidebar = (
        <Sidebar
        highlights={isRelationFiltered ? filteredRelationHighlights : relationHighlights}
          getHighlightById={getHighlightById}
          setIsActive={setIsActive}
          setHighlights={setVisibleHighlights}
          selectedMode={selectedMode}
          paraHighlights={paraHighlights}
        />
      );
    } else if (selectedMode === 'Events') {
      pdfloader = <PdfLoader document={url}>
      {(loadedPdfDocument) => {
        // Set the loaded PDF document state here
        setPdfDocument(loadedPdfDocument);
        return (
            <PdfHighlighter
              enableAreaSelection={(event) => event.altKey}
              pdfDocument={loadedPdfDocument}
              // onScrollAway={resetHash}
              utilsRef={(_pdfHighlighterUtils) => {
                highlighterUtilsRef.current = _pdfHighlighterUtils;
              }}
              pdfScaleValue={pdfScaleValue}
              selectionTip={<ExpandableTip addHighlight={(highlight, comment) => addHighlight(highlight, comment)} />}
              highlights={eventHighlights}
              style={{
                height: "calc(100% - 41px)",
              }}
              onPageChange={(page) => PDFpageChange(page)}
            >
              <HighlightContainer
                editHighlight={editHighlight}
                onContextMenu={handleContextMenu}
              />
            </PdfHighlighter>
        );
      }}
    </PdfLoader>

    sidebar = <EventSidebar
        highlights={eventHighlights}
        getHighlightById={getHighlightById}
        setIsActive={setIsActive}
        setHighlights={setVisibleHighlights}
        selectedMode={selectedMode}
        paraHighlights={paraHighlights}
      />
    } else {
    pdfloader = <PdfLoader document={url}>
      {(loadedPdfDocument) => {
        // Set the loaded PDF document state here
        setPdfDocument(loadedPdfDocument);
        return (
            <PdfHighlighter
              enableAreaSelection={(event) => event.altKey}
              pdfDocument={loadedPdfDocument}
              // onScrollAway={resetHash}
              utilsRef={(_pdfHighlighterUtils) => {
                highlighterUtilsRef.current = _pdfHighlighterUtils;
              }}
              pdfScaleValue={pdfScaleValue}

              highlights={paraHighlights}
              style={{
                height: "calc(100% - 41px)",
              }}
              onPageChange={(page) => PDFpageChange(page)}
            >
              <HighlightContainer
                editHighlight={editHighlight}
                onContextMenu={handleContextMenu}
              />
            </PdfHighlighter>
        );
      }}
    </PdfLoader>

    sidebar = <ParagraphSidebar
        highlights={paraHighlights}
        getHighlightById={getHighlightById}
        setIsActive={setIsActive}
        setHighlights={setHighlights}
      />
  }


  return (
    <LoadingOverlay
      active={isActive}
      spinner
      text="Saving ..."
      styles={{
        overlay: (base) => ({
          ...base,
          position: "fixed",
          top: 0,
          left: 0,
          width: "100vw",
          height: "100vh",
          zIndex: 9999,
        }),
      }}
    >
      <div className="App" style={{ display: "flex", height: "100vh" }}>
        <div
          style={{
            height: "100vh",
            width: "75vw",
            overflow: "hidden",
            position: "relative",
            flexGrow: 1,
          }}
        >
          <Toolbar setPdfScaleValue={(value) => setPdfScaleValue(value)} currentPage={currentPDFPage} totalPages={totalPages} setIsActive={setIsActive} />
          {pdfloader}
        </div>
        
        {/* Sidebar component */}
        {sidebar}

        <SettingSidebar
          highlights={highlights}
          paraHighlights={paraHighlights}
          relationHighlights={relationHighlights}
          eventHighlights={eventHighlights}
          filterHighlights={filterHighlights}
          filterRelations={filterRelations} // Pass filterRelations function
          resetFilter={resetFilter}
          resetRelationFilter={resetRelationFilter} // Pass resetRelationFilter function
          selectedMode={selectedMode}
          setSelectedMode={setSelectedMode}
          setIsActive={setIsActive}
        />
        {contextMenu && <ContextMenu {...contextMenu} />}
        <Tooltip title="Click to view document information" placement="left" arrow>
          <InfoIcon style={{  
              position: "fixed",
              bottom: "10px",
              right: "10px",
              zIndex: 1000,
              cursor: "pointer",
              color: hover ? "blue" : "gray" // Change color on hover
            }}
            onClick={toggleDialog}
            onMouseEnter={() => setHover(true)}
            onMouseLeave={() => setHover(false)}
          />
        </Tooltip>
        <Dialog 
          open={isDialogOpen} 
          onClose={toggleDialog} 
          maxWidth="xl" 
          PaperProps={{
            style: {
              borderRadius: '8px',
              backgroundColor: '#fafafa',
            }
          }}
        >
          <DialogTitle>
            <Typography variant="h5" component="div" fontWeight="bold">
              Document Information
            </Typography>
          </DialogTitle>
          <DialogContent dividers>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body1" sx={{ mb: 1 }}>
                <strong>Total Highlights:</strong> {highlights.length}
              </Typography>
              <Typography variant="body1" sx={{ mb: 1 }}>
                <strong>Model Update Time (NER and RE):</strong> July 15, 2024
              </Typography>
              <Typography variant="body1">
                <strong>PylyMinder Version:</strong> 3.2.0
              </Typography>
            </Box>

            <Divider sx={{ my: 3 }} />

            <Box sx={{ mt: 2 }}>
              <Typography variant="h6" component="div" fontWeight="bold" sx={{ mb: 2 }}>
                History:
              </Typography>
              <Timeline position="alternate">
                {history.map((event, idx) => (
                  <TimelineItem key={idx}>
                    <TimelineSeparator>
                      <TimelineDot color="primary" />
                      {idx < history.length - 1 && <TimelineConnector />}
                    </TimelineSeparator>
                    <TimelineContent>
                      <Typography
                        variant="subtitle1"
                        fontWeight="bold"
                        style={{ cursor: 'pointer', color: 'blue' }}
                        onClick={(e) => handleHistoryClick(e, event)}
                      >
                        {event.name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {event.upload_time}
                      </Typography>
                    </TimelineContent>
                  </TimelineItem>
                ))}
              </Timeline>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button 
              onClick={toggleDialog} 
              color="primary" 
              variant="contained"
              sx={{ textTransform: 'none', fontWeight: 'medium' }}
            >
              Close
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog
          open={isConfirmDialogOpen}
          onClose={() => setIsConfirmDialogOpen(false)}
          maxWidth="sm"
          PaperProps={{
            style: {
              borderRadius: '8px',
              backgroundColor: '#fff',
            },
          }}
        >
          <DialogTitle>
            <Typography variant="h6" fontWeight="bold">
              Confirm Revert
            </Typography>
          </DialogTitle>
          <DialogContent>
            <Typography variant="body1">
              Are you sure you want to revert to the selected history checkpoint?
              This action will overwrite any updates made since this checkpoint.
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => setIsConfirmDialogOpen(false)}
              color="secondary"
              variant="outlined"
              sx={{ textTransform: 'none', fontWeight: 'medium' }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleRevertConfirm}
              color="primary"
              variant="contained"
              sx={{ textTransform: 'none', fontWeight: 'medium' }}
            >
              Confirm
            </Button>
          </DialogActions>
        </Dialog>
        
      </div>
    </LoadingOverlay>
  );
};
  
export default ResultComponent;