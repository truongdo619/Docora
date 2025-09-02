import React, { useState, useEffect, useRef, useContext } from "react";
import type { Highlight } from "../react-pdf-highlighter-extended";
import "../style/Sidebar.css";
import { CommentedHighlight } from "../types";
import "../pdf_highlighter/style/TextHighlight.css";
import EditNoteIcon from '@mui/icons-material/EditNote';
import IconButton from '@mui/material/IconButton';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Button from '@mui/material/Button';
import { Divider, Tooltip } from "@mui/material";
import { TextareaAutosize as BaseTextareaAutosize } from '@mui/base/TextareaAutosize';
import { styled } from '@mui/system';
import axiosInstance from '../axiosSetup';
import { GlobalContext } from '../GlobalState';
import { useNavigate } from 'react-router-dom';

// Import from react-beautiful-dnd
import { DragDropContext, Draggable, DropResult } from "react-beautiful-dnd";
// Import our custom StrictModeDroppable
import { StrictModeDroppable } from "./StrictModeDroppable";

interface ParagraphSidebarProps {
  highlights: Array<CommentedHighlight>;
  getHighlightById: (id: string) => CommentedHighlight | undefined;
  setIsActive: (active: boolean) => void;
  setHighlights: React.Dispatch<React.SetStateAction<Array<CommentedHighlight>>>;
}

const updateHash = (highlight: Highlight) => {
  const hash = document.location.hash;
  const parts = hash.split('#');
  document.location.hash = parts[0] + "#" + parts[1] + "#highlight-" + highlight.id;
};

// Helper to reorder list items
const reorder = <T,>(list: T[], startIndex: number, endIndex: number): T[] => {
  const result = Array.from(list);
  const [removed] = result.splice(startIndex, 1);
  result.splice(endIndex, 0, removed);
  return result;
};

const ParagraphSidebar = ({
  highlights,
  getHighlightById,
  setIsActive,
  setHighlights
}: ParagraphSidebarProps) => {

  /* ----------------------------
   *    Styled Textarea
   * ---------------------------- */

  const blue = {
    100: '#DAECFF',
    200: '#b6daff',
    400: '#3399FF',
    500: '#007FFF',
    600: '#0072E5',
    900: '#003A75',
  };

  const grey = {
    50: '#F3F6F9',
    100: '#E5EAF2',
    200: '#DAE2ED',
    300: '#C7D0DD',
    400: '#B0B8C4',
    500: '#9DA8B7',
    600: '#6B7A90',
    700: '#434D5B',
    800: '#303740',
    900: '#1C2025',
  };

  const Textarea = styled(BaseTextareaAutosize)(
    ({ theme }) => `
      box-sizing: border-box;
      width: 50rem;
      font-family: 'IBM Plex Sans', sans-serif;
      font-size: 0.875rem;
      font-weight: 400;
      line-height: 1.5;
      padding: 8px 12px;
      border-radius: 8px;
      color: ${theme.palette.mode === 'dark' ? grey[300] : grey[900]};
      background: ${theme.palette.mode === 'dark' ? grey[900] : '#fff'};
      border: 1px solid ${theme.palette.mode === 'dark' ? grey[700] : grey[200]};
      box-shadow: 0px 2px 2px ${theme.palette.mode === 'dark' ? grey[900] : grey[50]};

      &:hover {
        border-color: ${blue[400]};
      }

      &:focus {
        border-color: ${blue[400]};
        box-shadow: 0 0 0 3px ${theme.palette.mode === 'dark' ? blue[600] : blue[200]};
      }

      &:focus-visible {
        outline: 0;
      }
    `
  );

  /* ----------------------------
   *    State
   * ---------------------------- */
  const [openEdit, setOpenEdit] = useState(false);
  const [currentHighlight, setCurrentHighlight] = useState<CommentedHighlight | null>(null);

  // Reordering
  const [openReorder, setOpenReorder] = useState(false);
  const [reorderedHighlights, setReorderedHighlights] =
    useState<CommentedHighlight[]>(highlights);

  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const globalContext = useContext(GlobalContext);
  const navigateTo = useNavigate();

  if (!globalContext) {
    throw new Error("GlobalContext must be used within a GlobalProvider");
  }

  const { documentId, updateId, setBratOutput, setDocumentId, setUpdateId } = globalContext;

  /* ----------------------------------
   *   HANDLERS
   * ---------------------------------- */

  // Highlight Click
  const handleHighlightClick = (highlight: Highlight) => {
    updateHash(highlight);
  };

  // Open edit dialog
  const editClick = (highlight: CommentedHighlight) => {
    setCurrentHighlight(highlight);
    setOpenEdit(true);
  };

  // Close edit dialog
  const handleCloseEdit = () => {
    setOpenEdit(false);
    setCurrentHighlight(null);
  };

  // Save changes to a single paragraph (Edit)
  const handleSaveEdit = async () => {
    if (!currentHighlight || !textareaRef.current || !documentId) return;

    setIsActive(true);

    // Update the content of the edited highlight
    currentHighlight.content.text = textareaRef.current.value;

    // Build data to send to backend
    const data = {
      document_id: documentId,
      update_id: updateId,
      paragraphs: highlights.map((highlight) => {
        if (highlight.id === currentHighlight?.id) {
          return textareaRef.current?.value || highlight.content.text;
        }
        return highlight.content.text;
      }),
    };

    try {
      const token = localStorage.getItem('accessToken');
      const response = await axiosInstance.post(
        `${import.meta.env.VITE_BACKEND_URL}/edit-paragraph`,
        data,
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        }
      );

      // console.log('Paragraphs updated successfully:', response.data);
      setBratOutput(response.data.brat_format_output);
      setDocumentId(response.data.document_id);
      setUpdateId(response.data.update_id);
      setHighlights(response.data.pdf_format_output);

      // Navigate to your /result route
      navigateTo('/result', {
        state: {
          highlights: response.data.pdf_format_output,
          url: `${import.meta.env.VITE_PDF_BACKEND_URL}/statics/${response.data.filename}`,
        },
      });
    } catch (error) {
      console.error('Error updating paragraphs:', error);
    } finally {
      setIsActive(false);
      handleCloseEdit();
    }
  };

  /* --------------------------------
   *  REORDER DIALOG & DRAG-AND-DROP
   * -------------------------------- */

  // Open reorder dialog
  const handleOpenReorder = () => {
    // Make a fresh copy of current highlights
    setReorderedHighlights([...highlights]);
    setOpenReorder(true);
  };

  // Close reorder dialog
  const handleCloseReorder = () => {
    setOpenReorder(false);
  };

  // Final event after drag finishes
  const onDragEnd = (result: DropResult) => {
    if (!result.destination) {
      return;
    }
    const newOrder = reorder(
      reorderedHighlights,
      result.source.index,
      result.destination.index
    );
    setReorderedHighlights(newOrder);
  };

  // Save newly reordered paragraphs to backend
  const handleSaveReorder = async () => {
    if (!documentId) return;

    setIsActive(true);

    const newParagraphsOrder = reorderedHighlights.map((h) => h.para_id);

    const data = {
      document_id: documentId,
      update_id: updateId,
      paragraphs: newParagraphsOrder,
    };

    try {
      const token = localStorage.getItem('accessToken');
      const response = await axiosInstance.post(
        `${import.meta.env.VITE_BACKEND_URL}/reorder-paragraph`,
        data,
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        }
      );

      // console.log('Paragraphs reordered successfully:', response.data);
      setBratOutput(response.data.brat_format_output);
      setDocumentId(response.data.document_id);
      setUpdateId(response.data.update_id);
      setHighlights(response.data.pdf_format_output);

      // Navigate to a result page (or stay in place if you want)
      navigateTo('/result', {
        state: {
          highlights: response.data.pdf_format_output,
          url: `${import.meta.env.VITE_PDF_BACKEND_URL}/statics/${response.data.filename}`,
        },
      });
    } catch (error) {
      console.error('Error reordering paragraphs:', error);
    } finally {
      setIsActive(false);
      handleCloseReorder();
    }
  };

  // Scroll to highlight if hash found
  useEffect(() => {
    const parts = document.location.hash.split("#");
    const lastPart = parts[parts.length - 1];
    if (lastPart) {
      const highlightElement = document.getElementById(lastPart);
      if (highlightElement) {
        highlightElement.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }, [highlights]);

  return (
    <div className="sidebar" style={{ width: "20vw", maxWidth: "1000px" }}>
      <div className="description" style={{ padding: "1rem" }}>
        <h2 style={{ marginBottom: "1rem" }}>
          Found <span className="total_entities_span">{highlights.length}</span> paragraphs in this document.
        </h2>

        <p style={{ fontSize: "15px", marginTop: "10px" }}>
          📝 If the paragraphs seem out of order, you can{" "}
          <span
            style={{
              color: "#007bff",
              cursor: "pointer",
              textDecoration: "none",
              fontWeight: "bold",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.textDecoration = "underline")}
            onMouseLeave={(e) => (e.currentTarget.style.textDecoration = "none")}
            onClick={handleOpenReorder}
          >
            revise the order
          </span>
          .
        </p>
      </div>

      <ul className="sidebar__highlights" style={{ overflow: "auto", paddingTop: "10px" }}>
        {highlights.map((highlight) => {
          const isSelected =
            document.location.hash.split("#").slice(-1)[0] === `highlight-${highlight.id}`;
          return (
            <li
              key={highlight.id}
              id={`highlight-${highlight.id}`}
              className={`sidebar__highlight ${isSelected ? 'sidebar__highlight--selected' : ''}`}
              onClick={() => handleHighlightClick(highlight)}
              style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}
            >
              <div style={{ flex: 1, width: '100%' }}>
                <div className="highlight_item_header">
                  <p className={"entity_point " + highlight.comment}>&nbsp;&nbsp;</p>
                  <strong>{highlight.comment + " " + (highlight.para_id + 1)}</strong>
                </div>
                {highlight.content.text && (
                  <blockquote>
                    {`${highlight.content.text.slice(0, 90).trim()} ...`}
                  </blockquote>
                )}
                {highlight.content.image && (
                  <div className="highlight__image__container" style={{ marginTop: "0.5rem" }}>
                    <img
                      src={highlight.content.image}
                      alt={"Screenshot"}
                      className="highlight__image"
                    />
                  </div>
                )}
              </div>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  width: '100%',
                  alignItems: 'center',
                  marginTop: '1rem'
                }}
              >
                <IconButton
                  color="primary"
                  aria-label="edit paragraph"
                  onClick={(e) => {
                    e.stopPropagation();
                    editClick(highlight);
                  }}
                >
                  <EditNoteIcon />
                </IconButton>
                <div className="highlight__location" style={{ marginLeft: 'auto' }}>
                  Page {highlight.position.boundingRect.pageNumber}
                </div>
              </div>
            </li>
          );
        })}
      </ul>

      {/* --- EDIT TEXT DIALOG --- */}
      <Dialog open={openEdit} onClose={handleCloseEdit} maxWidth="md">
        <DialogTitle sx={{ textAlign: "center" }}>
          Edit Text - Paragraph {currentHighlight ? currentHighlight.para_id + 1 : ''}
        </DialogTitle>
        <Divider />
        <DialogContent>
          <Textarea
            aria-label="maximum height"
            defaultValue={currentHighlight ? currentHighlight.content.text : ''}
            ref={textareaRef}
          />
        </DialogContent>
        <Divider />
        <DialogActions>
          <Button onClick={handleCloseEdit} color="primary" variant="outlined">
            Cancel
          </Button>
          <Button onClick={handleSaveEdit} color="primary" variant="contained">
            Save & Reload
          </Button>
        </DialogActions>
      </Dialog>

      {/* --- REORDER DIALOG (DRAG & DROP) --- */}
      <Dialog open={openReorder} onClose={handleCloseReorder} maxWidth="md" fullWidth>
        <DialogTitle sx={{ textAlign: "center" }}>Reorder Paragraphs</DialogTitle>
        <Divider />
        <DialogContent dividers>
          <DragDropContext onDragEnd={onDragEnd}>
            {/* Use our StrictModeDroppable instead of Droppable */}
            <StrictModeDroppable droppableId="paragraphsDroppable">
              {(provided) => (
                <ul
                  style={{ listStyle: 'none', padding: 0 }}
                  {...provided.droppableProps}
                  ref={provided.innerRef}
                >
                  {reorderedHighlights.map((highlight, index) => (
                    <Draggable
                      key={String(highlight.id)}
                      draggableId={String(highlight.id)}
                      index={index}
                    >
                      {(provided, snapshot) => (
                        <Tooltip key={highlight.id} title={highlight.content.text} arrow>
                          <li
                            ref={provided.innerRef}
                            {...provided.draggableProps}
                            {...provided.dragHandleProps}
                            style={{
                              userSelect: 'none',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              marginBottom: '1rem',
                              padding: '0.5rem',
                              border: '1px solid #ddd',
                              borderRadius: '5px',
                              backgroundColor: snapshot.isDragging
                                ? '#ececec'
                                : '#f9f9f9',
                              cursor: 'grab',
                              transition: 'background 0.2s ease-in-out',
                              ...provided.draggableProps.style,
                            }}
                          >
                            <div>
                              <strong>Paragraph {highlight.para_id + 1}</strong>:{" "}
                              {highlight.content.text.slice(0, 80)}...
                            </div>
                          </li>
                        </Tooltip>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </ul>
              )}
            </StrictModeDroppable>
          </DragDropContext>
        </DialogContent>
        <Divider />
        <DialogActions>
          <Button onClick={handleCloseReorder} color="primary" variant="outlined">
            Cancel
          </Button>
          <Button onClick={handleSaveReorder} color="primary" variant="contained">
            Save & Reload
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default ParagraphSidebar;
