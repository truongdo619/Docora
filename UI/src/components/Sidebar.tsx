import React, { useEffect, useState, useContext, useMemo } from "react";
import type { Highlight } from "../react-pdf-highlighter-extended";
import "../style/Sidebar.css";
import { CommentedHighlight } from "../types";
import "../pdf_highlighter/style/TextHighlight.css";
import EditNoteIcon from '@mui/icons-material/EditNote';
import CommentIcon from "@mui/icons-material/Comment";
import IconButton from '@mui/material/IconButton';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Divider from '@mui/material/Divider';
import InputLabel from '@mui/material/InputLabel';
import FormControl from '@mui/material/FormControl';
import DialogContentText from '@mui/material/DialogContentText';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import AddIcon from '@mui/icons-material/Add';
import StarIcon from '@mui/icons-material/Star';
import StarBorderIcon from '@mui/icons-material/StarBorder';
import Tooltip from '@mui/material/Tooltip';
import SplitButton from './SplitButton';
import DeleteIcon from '@mui/icons-material/Delete';
import EditedEntityComponent from './EditedEntityComponent';
import { GlobalContext } from '../GlobalState';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../axiosSetup';
import Pagination from '@mui/material/Pagination';
import { Box, List, ListItem, Snackbar, Checkbox, Typography, TextField, Alert } from '@mui/material';

interface SidebarProps {
  highlights: Array<CommentedHighlight>;
  getHighlightById: (id: string) => CommentedHighlight | undefined;
  setIsActive: (active: boolean) => void;
  setHighlights: React.Dispatch<React.SetStateAction<Array<CommentedHighlight>>>; // Add this line
  selectedMode: string;
  paraHighlights: Array<CommentedHighlight>; // <-- new prop
}

interface MatchedEntity {
  entity_id: string;
  entity_text: string;
  entity_type: string;
  para_id: number;
  page_number: number[];
  short_text?: string;
  head?: number;
  tail?: number;
}


const updateHash = (highlight: Highlight) => {
  document.location.hash += `#highlight-${highlight.id}`;
};

// Define the type for paragraph
interface Paragraph {
  entities: Array<[string, any, any]>; // Adjust the tuple type as needed
  // Add other properties if necessary
}

const Sidebar = ({ highlights, getHighlightById, setIsActive, setHighlights, selectedMode, paraHighlights }: SidebarProps) => {
  const globalContext = useContext(GlobalContext);
  
  // console.log("highlights", highlights)
  if (!globalContext) {
    throw new Error("GlobalContext must be used within a GlobalProvider");
  }
  const { bratOutput, documentId, updateId, setBratOutput, setDocumentId, setUpdateId, fileName, setFileName, settings } = globalContext;
  const navigateTo = useNavigate();
  const convertedBratOutput: Record<string, [string, any, any]> = {}; // Update the type
  bratOutput.forEach((paragraph: Paragraph, index: number) => {
    paragraph.entities.forEach(entity => {
      const convertedEntityId = `para${index}_${entity[0]}`; // Combine paragraph index with entity ID
      convertedBratOutput[convertedEntityId] = entity;
    });
  });

    // ---- Settings → types -----------------------------------------------------
  type EntityDef = { type: string; labels?: string[]; [k: string]: any };
  type RelationDef = { type: string; labels?: string[]; [k: string]: any };

  const entityTypes = useMemo<string[]>(
    () => ((settings?.entity_types as EntityDef[] | undefined)?.map(e => e.type)) ?? [],
    [settings?.entity_types]
  );

  const relationTypes = useMemo<string[]>(
    () => {
      const base = ((settings?.relation_types as RelationDef[] | undefined)?.map(r => r.type)) ?? [
        "has_property","has_value","has_amount","has_condition",
        "abbreviation_of","refers_to","synthesised_by","characterized_by"
      ];
      return base;
    },
    [settings?.relation_types]
  );

  useEffect(() => {
    if (!entityTypes.length) return;
    setEditableComment(prev => (prev && entityTypes.includes(prev)) ? prev : entityTypes[0]);
  }, [entityTypes]);


  const [dialogOpen, setDialogOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [maxDialogWidth, setMaxDialogWidth] = useState<'xs' | 'sm' | 'md' | 'lg' | 'xl' | false>('lg');
  const [selectedHighlight, setSelectedHighlight] = useState<CommentedHighlight | null>(null);
  const [editableComment, setEditableComment] = useState<string>('');
  const [editableUserComment, setEditableUserComment] = useState<string>('');
  const [tabValue, setTabValue] = useState(0);

  const [editingRelationIndex, setEditingRelationIndex] = useState<number | null>(null);
  const [editedRelationType, setEditedRelationType] = useState<string>('');

  const [newRelationType, setNewRelationType] = useState<string>('');
  const [newRelationTarget, setNewRelationTarget] = useState<string>('');
  const [selectionStart, setSelectionStart] = useState<number | null>(null);
  const [selectionEnd, setSelectionEnd] = useState<number | null>(null);
  const [confirmStatusOpen, setConfirmStatusOpen] = useState(false);

  const [openSnackbar, setOpenSnackbar] = useState(false);
  const [notification, setNotification] = useState('');
  const [notificationSeverity, setNotificationSeverity] = useState<'success' | 'error'>('success');
  const [matchedEntities, setMatchedEntities] = useState<MatchedEntity[]>([]);
  const [UpdateContentMatchedEntities, setUpdateContentMatchedEntities] = useState<any[]>([]);
  const [confirmUpdateMatchedEntitiesOpen, setConfirmUpdateMatchedEntitiesOpen] = useState(false);
  const [isReviewingMatchedEntities, setIsReviewingMatchedEntities] = useState(false);
  const [matchedEntitiesSelections, setMatchedEntitiesSelections] = useState<boolean[]>([]);
  const [allMatchedEntitiesSelected, setAllMatchedEntitiesSelected] = useState(true);

  const handleCloseSnackbar = () => {
    setOpenSnackbar(false);
  };





  // State for "adjust your selection" dialog
  const [openParaSelection, setOpenParaSelection] = useState(false);
  // Track which paragraphs are selected (default all checked)
  const [paragraphSelections, setParagraphSelections] = useState<boolean[]>(
    paraHighlights.map(ph => ph.visible !== undefined ? ph.visible : true)
  );


  // State to track if the "add relation" row should be shown
  const [showAddRelationRow, setShowAddRelationRow] = useState(false);

  // Define state for pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 30; // Set items per page to 30

  // Calculate total pages based on highlights length and itemsPerPage
  const totalPages = Math.ceil(highlights.length / itemsPerPage);

  // Determine the highlights to display on the current page
  const startIndex = (currentPage - 1) * itemsPerPage;
  const currentHighlights = highlights.slice(startIndex, startIndex + itemsPerPage);

  const [allParagraphsSelected, setAllParagraphsSelected] = useState(true);

  // Updated paragraph checkbox handler to keep the "All" box in sync:
  const handleParagraphCheckbox = (index: number) => {
    setParagraphSelections((prev) => {
      const updated = [...prev];
      updated[index] = !updated[index];
      // Update the "All" checkbox state if any box is unchecked
      setAllParagraphsSelected(updated.every(Boolean));
      return updated;
    });
  };

  // New function to toggle all paragraphs on/off:
  const handleAllParagraphsToggle = () => {
    const newVal = !allParagraphsSelected;
    setAllParagraphsSelected(newVal);
    setParagraphSelections(paragraphSelections.map(() => newVal));
  };


  // Handle page change
  const handlePageChange = (event, page) => {
    setCurrentPage(page);
  };

  // Reset currentPage to 1 whenever selectedMode changes
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedMode]);

    
  const handleHighlightClick = (highlight: Highlight) => {
    updateHash(highlight);
    // console.log(highlight);
    setSelectedHighlight(highlight);
  };

  const editClick = (highlight: CommentedHighlight) => {
    setSelectedHighlight(highlight);
    setDialogOpen(true);
  };
  
  useEffect(() => {
    if (selectedHighlight) {
      setEditableComment(selectedHighlight.comment || '');
      setEditableUserComment(selectedHighlight.user_comment || '');
      setSelectionStart(convertedBratOutput[selectedHighlight.id][2][0][0]);
      setSelectionEnd(convertedBratOutput[selectedHighlight.id][2][0][1]);
    }
  }, [selectedHighlight]);

  const handleDialogClose = () => {
    setDialogOpen(false);
    setSelectedHighlight(null);
    setTabValue(0);
    setShowAddRelationRow(false);
    setNewRelationType('');
    setNewRelationTarget('');
    setConfirmStatusOpen(false);
    setEditableUserComment('');
  };

  const handleOpenParaSelection = () => {
    setOpenParaSelection(true);
  };
  
  const handleCloseParaSelection = () => {
    setOpenParaSelection(false);
  };
  
  
  // When user hits "Save & Reload" in that dialog
  // Here we simply filter out any highlights that belong
  // to unchecked paragraphs. Adjust as needed.

  const handleSaveParagraphSelection = async () => {
    try {
      setIsActive(true);
      const data = {
        document_id: documentId,
        update_id: updateId,
        visible_list: paragraphSelections
      };

      console.log("Payload to /set-visible:", data);
      const token = localStorage.getItem('accessToken');
      const response = await axiosInstance.post(
        `${import.meta.env.VITE_BACKEND_URL}/set-visible`,
        data,
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        }
      );

      // After success, set new highlights
      // If you need, also update other states (bratOutput, fileName, etc.)
      setBratOutput(response.data.brat_format_output);
      setDocumentId(response.data.document_id); // Store documentId in GlobalState
      setUpdateId(response.data.update_id);
      setHighlights(response.data.pdf_format_output);
      setFileName(response.data.filename);
      navigateTo('/result', { 
        state: { 
          highlights: response.data.pdf_format_output, 
          url: `${import.meta.env.VITE_PDF_BACKEND_URL}/statics/${response.data.filename}`
        }
      });
    } catch (error) {
      console.error("Error updating visible list:", error);
    } finally {
      setOpenParaSelection(false);
      setIsActive(false);
    }
  };


  const handleEntitySaveAndReload = async () => {
    setIsActive(true);
    const data = {
        document_id: documentId,
        update_id: updateId,
        id: selectedHighlight?.id,
        head_pos: selectionStart,
        tail_pos: selectionEnd,
        type: editableComment,
        user_comment: editableUserComment
    };
    // console.log('data:', data);
    // console.log('selectedHighlight:', selectedHighlight);
    try {
        const token = localStorage.getItem('accessToken');
        const response = await axiosInstance.post(
            `${import.meta.env.VITE_BACKEND_URL}/update-entity`,
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
        setHighlights(response.data.pdf_format_output);
        setFileName(response.data.filename);
        navigateTo('/result', { 
          state: { 
            highlights: response.data.pdf_format_output, 
            url: `${import.meta.env.VITE_PDF_BACKEND_URL}/statics/${response.data.filename}`
          }
        });
        // ✅ Set snackbar for success

        setNotification('Entity saved successfully.');
        setNotificationSeverity('success');
        const matched = response.data.matched_entities || [];
        setUpdateContentMatchedEntities(response.data.update_content_matched_entities || []);
        if (matched.length > 0) {
          setMatchedEntities(matched); // store for further usage
          setUpdateContentMatchedEntities(response.data.update_content || []);
          setConfirmUpdateMatchedEntitiesOpen(true); // show Yes/No dialog
      }
    } catch (error) {
      console.error('Error updating paragraphs:', error);
      setNotification('Failed to save entity. Please try again.');
      setNotificationSeverity('error');
    } finally {
      setSelectedHighlight(null);
      setDialogOpen(false);
      setConfirmOpen(false);
      setIsActive(false);
      setOpenSnackbar(true);
    }
  };

  const handleSaveMatchedEntitiesSelection = async () => {
    // 1️⃣  Build list_update from the check-marked entities
    setIsActive(true);
    const list_update = matchedEntities
      .filter((_, i) => matchedEntitiesSelections[i])   // only those the user ticked
      .map(({ para_id, page_number, entity_id }) => ({
        para_id,
        page_number,
        entity_id,
      }));
    
    // 2️⃣  Early exit if the user deselected everything
    if (list_update.length === 0) {
      setNotification('No entities selected.');
      setNotificationSeverity('error');
      setOpenSnackbar(true);
      return;
    }

    // 3️⃣  Assemble the new payload
    const payload = {
      list_update,
      old_entity: UpdateContentMatchedEntities.old_entity, // already supplied by backend
      new_entity: UpdateContentMatchedEntities.new_entity, // already supplied by backend
      document_id: documentId,
      update_id: updateId,
    };

    console.log("payload:", payload);
    try {
      const token = localStorage.getItem('accessToken');
      const response = await axiosInstance.post(
        `${import.meta.env.VITE_BACKEND_URL}/apply-update`, // ← keep your endpoint
        payload,
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        },
      );
      console.log('Paragraphs updated successfully:', response.data);
      setBratOutput(response.data.brat_format_output);
      setDocumentId(response.data.document_id); // Store documentId in GlobalState
      setUpdateId(response.data.update_id);
      setHighlights(response.data.pdf_format_output);
      setFileName(response.data.filename);
      navigateTo('/result', { 
        state: { 
          highlights: response.data.pdf_format_output, 
          url: `${import.meta.env.VITE_PDF_BACKEND_URL}/statics/${response.data.filename}`
        }
      });

      setNotification('Selected entities updated successfully.');
      setNotificationSeverity('success');
    } catch (error) {
      console.error(error);
      setNotification('Failed to update selected entities.');
      setNotificationSeverity('error');
    } finally {
      setOpenSnackbar(true);
      setConfirmUpdateMatchedEntitiesOpen(false);
      setIsReviewingMatchedEntities(false);
      setIsActive(false);
    }
  };




  const handleDelete = async () => {
    setIsActive(true);
    const data = {
        document_id: documentId,
        update_id: updateId,
        ids: [selectedHighlight?.id],
    };
    // console.log('data:', data);
    // console.log('selectedHighlight:', selectedHighlight);
    try {
        const token = localStorage.getItem('accessToken');
        const response = await axiosInstance.post(
            `${import.meta.env.VITE_BACKEND_URL}/delete-entity`,
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
        setDocumentId(response.data.document_id); // Store documentId in GlobalState
        setUpdateId(response.data.update_id);
        setHighlights(response.data.pdf_format_output);
        setFileName(response.data.filename);
        navigateTo('/result', { 
          state: { 
            highlights: response.data.pdf_format_output, 
            url: `${import.meta.env.VITE_PDF_BACKEND_URL}/statics/${response.data.filename}`
          }
        });
    } catch (error) {
        console.error('Error updating paragraphs:', error);
    } finally {
        setSelectedHighlight(null);
        setDialogOpen(false);
        setConfirmOpen(false);
        setIsActive(false);
    }
    

  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleEditRelation = (index: number) => {
    if (selectedHighlight && selectedHighlight.relations) {
      setEditingRelationIndex(index);
      setEditedRelationType(selectedHighlight.relations[index].type || '');
    }
  };

  const handleDeleteRelation = (index: number) => {
    if (selectedHighlight && selectedHighlight.relations) {
      selectedHighlight.relations.splice(index, 1); // Remove the relation at the specified index
      setHighlights([...highlights]); // Trigger a re-render by updating the highlights
    }
  };

  const handleRelationTypeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setEditedRelationType(event.target.value);
  };

  const handleSaveRelationType = () => {
    if (selectedHighlight && selectedHighlight.relations && editingRelationIndex !== null) {
      selectedHighlight.relations[editingRelationIndex].type = editedRelationType;
      setEditingRelationIndex(null);
    }
  };

  const handleCancelEdit = () => {
    setEditingRelationIndex(null);
  };

  const handleAddRelation = () => {
    if (newRelationType && newRelationTarget) {
      const newRelation = {
        type: newRelationType,
        arg_id: newRelationTarget,
        arg_type: getHighlightById(newRelationTarget)?.comment || '',
        arg_text: getHighlightById(newRelationTarget)?.content.text || '',
      };
      if (selectedHighlight) {
        if (!selectedHighlight.relations) {
          selectedHighlight.relations = [];
        }
        selectedHighlight.relations.push(newRelation);
      }
      setNewRelationType('');
      setNewRelationTarget('');
    }
  };

  const handleAddButtonClick = () => {
    setShowAddRelationRow(true);
  };

  
  // const handleCommentSaveAndReload = async () => {
  //   if (!selectedHighlight) return;
  //   setIsActive(true);
  //   const data = {
  //     document_id: documentId,
  //     update_id: updateId,
  //     id: selectedHighlight.id,
  //     user_comment: editableUserComment
  //   };
  //   try {
  //     const token = localStorage.getItem('accessToken');
  //     const response = await axiosInstance.post(`${import.meta.env.VITE_BACKEND_URL}/update-comment`, data, {
  //       headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
  //     });
  //     setBratOutput(response.data.brat_format_output);
  //     setDocumentId(response.data.document_id);
  //     setUpdateId(response.data.update_id);
  //     setHighlights(response.data.pdf_format_output);
  //   } catch (error) {
  //     console.error('Error updating comment:', error);
  //   } finally {
  //     handleDialogClose();
  //     setIsActive(false);
  //   }
  // };

  
  const handleSaveAndReload = () => {
    if (tabValue === 0) {
      handleEntitySaveAndReload();
    } else if (tabValue === 1) {
      setDialogOpen(false);
      handleRelationSaveAndReload();
    }
    else if (tabValue === 2) {
      handleEntitySaveAndReload();
    }
  };

  const handleRelationSaveAndReload = async () => {
    setIsActive(true);
  
    // Prepare data for the server
    const data = {
      document_id: documentId,
      update_id: updateId,
      entity_id: selectedHighlight?.id,
      relations: selectedHighlight?.relations,
    };
    
    // console.log('data:', data);
    try {
      const token = localStorage.getItem('accessToken');
      const response = await axiosInstance.post(
        `${import.meta.env.VITE_BACKEND_URL}/update-relations`,
        data,
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        }
      );
  
      // console.log('Relations updated successfully:', response.data);
      setBratOutput(response.data.brat_format_output);
      setDocumentId(response.data.document_id); // Update documentId in GlobalState
      setUpdateId(response.data.update_id);
      setHighlights(response.data.pdf_format_output);
  
      // Navigate to the result page to display the updated highlights
      navigateTo('/result', { 
        state: { 
          highlights: response.data.pdf_format_output, 
          url: `${import.meta.env.VITE_PDF_BACKEND_URL}/statics/${response.data.filename}` 
        }
      });
    } catch (error) {
      console.error('Error updating relations:', error);
    } finally {
      setSelectedHighlight(null);
      setDialogOpen(false);
      setConfirmOpen(false);
      setIsActive(false);
    }
  };

  const handleEntitySelectionChange = (start: number, end: number) => {
    setSelectionStart(start);
    setSelectionEnd(end);
    console.log("Selection changed:", start, end);
  };

  useEffect(() => {
    const hash = document.location.hash.split("#")[document.location.hash.split("#").length - 1];
  
    // Find the index of hightlight in the highlights array using the ids
    const highlightIndex = highlights.findIndex((highlight) => `highlight-${highlight.id}` === hash);
    if (highlightIndex !== -1){
      setCurrentPage(Math.floor(highlightIndex / itemsPerPage) + 1);
    }
    // Set delay to ensure the element is rendered before scrolling
    setTimeout(() => {
      if (hash) {
        const highlightElement = document.getElementById(hash);
        if (highlightElement) {
          highlightElement.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    }, 100);
  }, [document.location.hash]);


  const handleStarClick = (highlight: CommentedHighlight) => {
    setSelectedHighlight(highlight);
    setConfirmStatusOpen(true);
  };


  const handleConfirmStar = async () => {
    if (!selectedHighlight) return;

    try {
      setIsActive(true);
      const newStatus = selectedHighlight.edit_status === "confirmed" ? "none" : "confirmed";
      const data = {
        document_id: documentId,
        update_id: updateId,
        id: selectedHighlight.id,
      };

      const token = localStorage.getItem('accessToken');
      const response = await axiosInstance.post(
        `${import.meta.env.VITE_BACKEND_URL}/change-edit-status`,
        data,
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        }
      );
      console.log('Status updated successfully:', response.data);
      // Update the local highlights with the new status
      setHighlights((prevHighlights) => 
        prevHighlights.map((highlight) =>
          highlight.id === selectedHighlight.id
            ? { ...highlight, edit_status: newStatus }
            : highlight
        )
      );

      console.log('Status updated successfully:', response.data);
    } catch (error) {
      console.error('Error updating status:', error);
    } finally {
      setConfirmStatusOpen(false);
      setSelectedHighlight(null);
      setIsActive(false);
    }
  };

  const renderStarButton = (highlight) => {
    const isConfirmed = highlight.edit_status === "confirmed";
    return (
      <Tooltip title={isConfirmed ? "This item has been confirmed by the user" : "This item has not been confirmed yet"}>
        <IconButton 
          color="primary" 
          aria-label={isConfirmed ? "confirmed" : "unconfirmed"} 
          onClick={(e) => {e.stopPropagation(); handleStarClick(highlight)}}
        >
          {isConfirmed ? <StarIcon /> : <StarBorderIcon />}
        </IconButton>
      </Tooltip>
    );
  };


  return (
    <div className="sidebar" style={{ width: "20vw", maxWidth: "1000px" }}>
      <div className="description" style={{ padding: "1rem" }}>
        <h2 style={{ marginBottom: "1rem" }}>
          Found <span className="total_entities_span">{highlights.length}</span> entities in this document.
        </h2>
        <p>
          <small>
            
          </small>
        </p>
        <p style={{ fontSize: "15px", marginTop: "10px" }}>
        🌟 To highlight a new entity, select the text you want and click "Add Highlight".
        </p>


        <p style={{ fontSize: "15px", marginTop: "10px" }}>
          📝 To annotate results for specific sections of the document, please{" "}
          <span
            style={{
              color: "#007bff",
              cursor: "pointer",
              textDecoration: "none",
              fontWeight: "bold",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.textDecoration = "underline")}
            onMouseLeave={(e) => (e.currentTarget.style.textDecoration = "none")}
            onClick={handleOpenParaSelection}
          >
            adjust your selection
          </span>
          .
        </p>

      </div>

      {/* Render paginated highlights */}
      <ul className="sidebar__highlights" style={{ overflow: "auto", paddingTop: "10px" }}>
        {currentHighlights.map((highlight, index) => (
          <li
            key={index}
            id={`highlight-${highlight.id}`}
            className={`sidebar__highlight ${document.location.hash.split("#")[document.location.hash.split("#").length - 1] === `highlight-${highlight.id}` ? 'sidebar__highlight--selected' : ''}`}
            onClick={() => handleHighlightClick(highlight)}
            style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}
          >
            <div style={{ flex: 1, width: '100%', overflow: "hidden" }}>
              <div className="highlight_item_header">
                <p className={"entity_point " + highlight.comment}>&nbsp;&nbsp;</p>
                <strong>{highlight.comment}</strong>
              </div>
              {highlight.content.text && (
                <blockquote style={{ fontSize: "0.9rem", overflow: "hidden", textOverflow: "ellipsis" }}> 
                  {`${highlight.content.text.slice(0, 60).trim()}`}
                </blockquote>
              )}
              <ul style={{ fontSize: "0.8rem", overflow: "hidden", textOverflow: "ellipsis" }}>
                {highlight.relations &&
                  highlight.relations.map((relation, index) => (
                    <li key={index}>
                      <i style={{ marginLeft: "0rem" }}>{relation.type}</i>
                      <br />
                      <strong style={{ marginLeft: "1rem" }}>
                        {relation.arg_type}: {relation.arg_text}
                      </strong>
                    </li>
                  ))}
              </ul>
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

            <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center', marginTop: '1.0rem' }}>
              <Tooltip title="Click to revise annotation">
                <IconButton color="primary" aria-label="edit paragraph" onClick={(e) => {e.stopPropagation(); editClick(highlight)}}>
                  <EditNoteIcon />
                </IconButton>
              </Tooltip>
              {/* Add a star button with a tooltip */}
              {highlight.comment && renderStarButton(highlight)}
              

              {
                highlight.user_comment && highlight.user_comment.length > 0 &&
                <Tooltip
                  title={'Show annotation comment'}
                >
                  <IconButton
                    aria-label="comment"
                    onClick={(e) => {}}
                  >
                    <CommentIcon  color="primary" />
                  </IconButton>
                </Tooltip>
              }

              <div className="highlight__location" style={{ marginLeft: 'auto' }}>
                Page {highlight.position.boundingRect.pageNumber}
              </div>
            </div>
          </li>
        ))}
      </ul>

      {/* Pagination Controls */}
      {/* MUI Pagination Controls */}
      <div
        className="pagination-controls"
        style={{
          position: "fixed",
          bottom: 0,
          width: "18vw",
          maxWidth: "1000px",
          padding: "10px 0",
          backgroundColor: "white",
          display: "flex",
          justifyContent: "center",
        }}
      >
        <Pagination 
          count={totalPages} 
          page={currentPage} 
          siblingCount={0}
          onChange={handlePageChange} 
          color="primary" 
          variant="outlined" 
          shape="rounded"
        />
      </div>

      <Dialog 
        open={dialogOpen} 
        onClose={handleDialogClose}
        fullWidth={true}
        maxWidth={maxDialogWidth}
      >
        <DialogTitle style={{ textAlign: 'center' }}>Edit Highlight</DialogTitle>
        <DialogContent>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="Entity and Relation tabs">
            <Tab label="Entity" />
            <Tab label="Relation" />
            <Tab label="Comment" />
          </Tabs>
          <Box role="tabpanel" hidden={tabValue !== 0} id="entity-tabpanel" aria-labelledby="entity-tab">
            {selectedHighlight ? (
            <>
              <FormControl fullWidth margin="normal">
                <InputLabel id="entity-type-label">Entity Type</InputLabel>
                <Select
                  labelId="entity-type-label"
                  value={editableComment}
                  onChange={(e) => setEditableComment(e.target.value)}
                  label="Entity Type"
                  fullWidth
                >
                  {entityTypes.map(t => (
                    <MenuItem key={t} value={t}>{t}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              <EditedEntityComponent  
                text={bratOutput[parseInt(selectedHighlight.id.split("_")[0].match(/\d+/)?.[0] || "0", 10)].text}
                defaultStart={convertedBratOutput[selectedHighlight.id][2][0][0]} 
                defaultEnd={convertedBratOutput[selectedHighlight.id][2][0][1]}
                onTextChange={(newText) => {console.log("Text changed:", newText)}}   
                onSelectionChange={handleEntitySelectionChange}
                entityType={editableComment}
              />
              {/* <TextField
                label="Content"
                value={editableContent}
                onChange={(e) => setEditableContent(e.target.value)}
                multiline
                fullWidth
                margin="normal"
                variant="outlined"/> */}
            </>
            ) : (
              <p>No highlight selected.</p>
            )}
          </Box>

          <Box role="tabpanel" hidden={tabValue !== 1} id="relation-tabpanel" aria-labelledby="relation-tab">
            {selectedHighlight ? (
              <TableContainer component={Paper}>
                <Table sx={{ minWidth: 650 }} aria-label="simple table">
                  <TableHead>
                    <TableRow>
                      <TableCell style={{fontWeight: "bold"}}>Subject Entity</TableCell>
                      <TableCell style={{fontWeight: "bold"}}>Relation</TableCell>
                      <TableCell style={{fontWeight: "bold"}}>Object Entity</TableCell>
                      <TableCell style={{fontWeight: "bold"}}>Action</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {(selectedHighlight.relations ?? []).map((relation, index) => (
                        <TableRow key={index}>
                          <TableCell>
                            <SplitButton 
                              filledText={selectedHighlight.comment} 
                              outlinedText={
                                (selectedHighlight.content.text ?? '').length > 30 
                                  ? `${(selectedHighlight.content.text ?? '').slice(0, 30).trim()}...` 
                                  : selectedHighlight.content.text ?? ''
                              } 
                              entityType={selectedHighlight.comment} 
                            />
                          </TableCell>
                          <TableCell style={{ fontStyle: 'italic', minWidth: '110px' }}>
                            {editingRelationIndex === index ? (
                              <FormControl fullWidth>
                                <Select
                                  value={editedRelationType}
                                  onChange={(e) => setEditedRelationType(e.target.value)}
                                  onBlur={handleSaveRelationType}
                                  autoFocus
                                >
                                  {relationTypes.map(rt => (
                                    <MenuItem key={rt} value={rt}>{rt}</MenuItem>
                                  ))}
                                </Select>
                              </FormControl>
                            ) : (
                              <span onClick={() => handleEditRelation(index)}>{relation.type}</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <SplitButton 
                              filledText={relation.arg_type} 
                              outlinedText={
                                relation.arg_text.length > 30
                                  ? `${relation.arg_text.slice(0, 30).trim()}...` 
                                  : relation.arg_text
                              } 
                              entityType={relation.arg_type} 
                            />
                          </TableCell>
                          <TableCell>
                            {/* <IconButton aria-label="delete relation" onClick={() => {}}>
                              <DeleteIcon />
                            </IconButton> */}
                            <IconButton aria-label="delete relation" onClick={() => handleDeleteRelation(index)}>
                              <DeleteIcon />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    {showAddRelationRow && (
                      <TableRow>
                        <TableCell>
                          <SplitButton 
                            filledText={selectedHighlight.comment} 
                            outlinedText={
                              (selectedHighlight.content.text ?? '').length > 30 
                                ? `${(selectedHighlight.content.text ?? '').slice(0, 30).trim()}...` 
                                : selectedHighlight.content.text ?? ''
                            } 
                            entityType={selectedHighlight.comment} 
                          />
                        </TableCell>
                        <TableCell  style={{ minWidth: '110px' }}>
                        <FormControl fullWidth>
                          <InputLabel id="relation-type-label">Relation Type</InputLabel>
                          <Select
                            labelId="relation-type-label"
                            value={newRelationType}
                            label="Relation Type"
                            onChange={(e) => setNewRelationType(e.target.value)}
                          >
                            <MenuItem value={"has_property"}>has_property</MenuItem>
                            <MenuItem value={"has_value"}>has_value</MenuItem>
                            <MenuItem value={"has_amount"}>has_amount</MenuItem>
                            <MenuItem value={"has_condition"}>has_condition</MenuItem>
                            <MenuItem value={"abbreviation_of"}>abbreviation_of</MenuItem>
                            <MenuItem value={"refers_to"}>refers_to</MenuItem>
                            <MenuItem value={"synthesised_by"}>synthesised_by</MenuItem>
                            <MenuItem value={"characterized_by"}>characterized_by</MenuItem>
                          </Select>
                        </FormControl>
                        </TableCell>
                        <TableCell  style={{ minWidth: '110px' }}>
                          <FormControl fullWidth>
                            <InputLabel id="relation-target-label">Target Entity</InputLabel>
                            <Select label="Target Entity" labelId="relation-target-label" value={newRelationTarget} onChange={(e) => setNewRelationTarget(e.target.value)}>
                              {highlights
                              .filter((highlight) => selectedHighlight.id.split("_")[0] === highlight.id.split("_")[0] && highlight.id !== selectedHighlight.id).map((highlight) => (
                                <MenuItem key={highlight.id} value={highlight.id}>
                                  {highlight.comment + ': ' + highlight.content.text}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                        </TableCell>
                        <TableCell>
                          <Button variant="contained" color="primary" onClick={handleAddRelation}>
                            Add
                          </Button>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <p>No highlight selected.</p>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-start', marginTop: '1rem' }}>
              <IconButton 
                color="primary" 
                onClick={handleAddButtonClick} 
                style={{
                  borderRadius: '50%',  // Round border
                  border: '2px solid',   // Add border
                  padding: '0px',       // Ensure sufficient padding for round shape
                }}
              >
                <AddIcon />
              </IconButton>
            </div>
          </Box>


          <Box role="tabpanel" hidden={tabValue !== 2} id="comment-tabpanel">
            {selectedHighlight ? (
              <TextField
                label="Comment"
                value={editableUserComment}
                onChange={(e)=>setEditableUserComment(e.target.value)}
                multiline
                rows={4}
                fullWidth
                margin="normal"
              />
            ) : (<p>No highlight selected.</p>)}
          </Box>

        </DialogContent>
        <DialogActions style={{ justifyContent: 'space-between', padding: "20px" }}>
          {tabValue === 0 && (
              <Button onClick={() => setConfirmOpen(true)} color="error" variant="contained">
                Delete
              </Button>
          )}
          <div></div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <Button onClick={handleDialogClose} color="primary" variant="outlined">
              Cancel
            </Button>
            <Button onClick={handleSaveAndReload} color="primary" variant="contained">
              Save & Reload
            </Button>
          </div>
        </DialogActions>
      </Dialog>

      <Dialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
      >
        <DialogTitle style={{ textAlign: 'center' }}>Confirm Deletion</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete this highlight?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)} color="primary">
            Cancel
          </Button>
          <Button onClick={handleDelete} color="secondary">
            Delete
          </Button>
        </DialogActions>
      </Dialog>


      <Dialog open={confirmStatusOpen} onClose={handleDialogClose}>
        <DialogTitle style={{ textAlign: 'center' }}>
          {selectedHighlight?.edit_status === "none" ? "Confirm Status Change" : "Confirm Deletion"}
        </DialogTitle>
        <DialogContent>
          <p>
            Are you sure you want to {selectedHighlight?.edit_status === "none" ? "confirm this highlight?" : "unconfirm this highlight?"}
          </p>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogClose} color="primary">
            Cancel
          </Button>
          <Button onClick={handleConfirmStar} color="primary" variant="contained">
            Confirm
          </Button>
        </DialogActions>
      </Dialog>

          
    {/* NEW Dialog: "Adjust Your Selection" */}
    <Dialog
    open={openParaSelection}
    onClose={handleCloseParaSelection}
    maxWidth="md"
    fullWidth
    PaperProps={{
      style: {
        borderRadius: '8px',
        backgroundColor: '#fafafa',
      },
    }}
    >
      <DialogTitle style={{ textAlign: 'center' }}>
        Adjust Your Paragraph Selection
      </DialogTitle>
      <Divider />
      <DialogContent dividers>
        {/* "Enable/Disable All" checkbox outside the paragraphs list */}
        <Box sx={{ display: "flex", alignItems: "center", marginBottom: "1rem" }}>
          <Checkbox
            checked={allParagraphsSelected}
            onChange={handleAllParagraphsToggle}
          />
          <Typography variant="body1">Enable/Disable All</Typography>
        </Box>

        {/* List of paragraphs with a tooltip and individual checkboxes */}
        <List>
          {paraHighlights.map((para, i) => {
            const shortPreview =
              para.content.text.slice(0, 150) +
              (para.content.text.length > 150 ? "..." : "");
            return (
              <ListItem
                key={i}
                dense
                sx={{
                  userSelect: "none",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "1rem",
                  padding: "0.5rem",
                  border: "1px solid #ddd",
                  borderRadius: "5px",
                  backgroundColor: "#f9f9f9",
                  cursor: "pointer",
                  transition: "background 0.2s ease-in-out",
                  ":hover": {
                    backgroundColor: "#ececec",
                  },
                }}
              >
                <Tooltip title={para.content.text} arrow>
                  <Box sx={{ flexGrow: 1 }}>
                    <Typography variant="subtitle2">
                      Paragraph {para.para_id + 1} - {para.comment}
                    </Typography>
                    <Typography variant="body2" sx={{ color: "#555" }}>
                      {shortPreview}
                    </Typography>
                  </Box>
                </Tooltip>

                {/* Individual paragraph checkbox */}
                <Checkbox
                  edge="end"
                  checked={paragraphSelections[i]}
                  onChange={() => handleParagraphCheckbox(i)}
                  tabIndex={-1}
                  disableRipple
                />
              </ListItem>
            );
          })}
        </List>
      </DialogContent>
      <Divider />
      <DialogActions>
        <Button onClick={handleCloseParaSelection} color="primary" variant="outlined">
          Cancel
        </Button>
        <Button onClick={handleSaveParagraphSelection} color="primary" variant="contained">
          Save & Reload
        </Button>
      </DialogActions>
    </Dialog>

    <Snackbar
      open={openSnackbar}
      autoHideDuration={6000}
      onClose={handleCloseSnackbar}
      anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
    >
      <Alert
        onClose={handleCloseSnackbar}
        severity={notificationSeverity}
        sx={{ width: '100%' }}
      >
        {notification}
      </Alert>
    </Snackbar>

    <Dialog
      open={confirmUpdateMatchedEntitiesOpen}
      onClose={() => {
        setConfirmUpdateMatchedEntitiesOpen(false);
        setIsReviewingMatchedEntities(false);
      }}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle sx={{ textAlign: 'center' }}>
        {isReviewingMatchedEntities
          ? 'Review & Apply to Matched Entities'
          : 'Apply Revision to Similar Entities?'}

        {isReviewingMatchedEntities && (
          <Box mt={1}>
            <Typography variant="body2" textAlign="center">
              {UpdateContentMatchedEntities.old_entity.entity_type}:{' '}
              <span className={`${UpdateContentMatchedEntities.old_entity.entity_type}`}>
                {UpdateContentMatchedEntities.old_entity.entity_text}
              </span>
              {' → '}
              {UpdateContentMatchedEntities.new_entity.entity_type}:{' '}
              <span className={`${UpdateContentMatchedEntities.new_entity.entity_type}`}>
                {UpdateContentMatchedEntities.new_entity.entity_text}
              </span>
            </Typography>
          </Box>
        )}
      </DialogTitle>


      <DialogContent dividers>
        {isReviewingMatchedEntities ? (
          <>
           {/* Enable/Disable All */}
            <Box sx={{ display: "flex", alignItems: "center" }}>
              <Checkbox
                checked={allMatchedEntitiesSelected}
                onChange={() => {
                  const newValue = !allMatchedEntitiesSelected;
                  setAllMatchedEntitiesSelected(newValue);
                  setMatchedEntitiesSelections(new Array(matchedEntities.length).fill(newValue));
                }}
              />
              <Typography variant="body1">Enable/Disable All</Typography>
            </Box>

            {/* Matched entity list */}
            <List>
              {matchedEntities.map((entity, i) => {
                return (
                  <ListItem
                    key={i}
                    dense
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "0.5rem",
                      border: "1px solid #ddd",
                      borderRadius: "5px",
                      marginBottom: "0.75rem",
                      backgroundColor: "#f9f9f9",
                    }}
                  >
                    <Tooltip title={entity.entity_text} arrow>
                      <Box sx={{ flexGrow: 1, paddingRight: 2 }}>
                        <Typography variant="subtitle2">
                          Paragraph: {entity.para_id + 1} – Page: {entity.page_number?.[0]}
                        </Typography>
                        <Typography variant="body2" sx={{ color: "#555" }}>
                          {"... "}
                          {entity.short_text?.slice(0, entity.head)}
                          <span className={`${entity.entity_type}`}>
                            {entity.entity_text}
                          </span>
                          {entity.short_text?.slice(entity.tail)}
                          {" ..."}
                        </Typography>
                      </Box>
                    </Tooltip>

                    <Checkbox
                      edge="end"
                      checked={matchedEntitiesSelections[i] || false}
                      onChange={() => {
                        const updated = [...matchedEntitiesSelections];
                        updated[i] = !updated[i];
                        setMatchedEntitiesSelections(updated);
                        setAllMatchedEntitiesSelected(updated.every(Boolean));
                      }}
                    />
                  </ListItem>
                );
              })}
            </List>
          </>
        ) : (
          <>
            <Typography variant="body1" gutterBottom>
              We found <strong>{matchedEntities.length}</strong> other entities in the document that have
              the <strong>same span text</strong> and <strong>original entity type</strong> as the one you just revised.
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Would you like to review and apply the same revision to these matched entities as well?
            </Typography>
          </>
        )}
      </DialogContent>

      <DialogActions>
        {isReviewingMatchedEntities ? (
          <>
            <Button
              onClick={() => {
                setConfirmUpdateMatchedEntitiesOpen(false);
                setIsReviewingMatchedEntities(false);
              }}
              color="primary"
              variant="outlined"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSaveMatchedEntitiesSelection}
              color="primary"
              variant="contained"
            >
              Save & Reload
            </Button>
          </>
        ) : (
          <>
            <Button
              onClick={() => setConfirmUpdateMatchedEntitiesOpen(false)}
              color="primary"
            >
              No
            </Button>
            <Button
              onClick={() => {
                setIsReviewingMatchedEntities(true);
                setMatchedEntitiesSelections(new Array(matchedEntities.length).fill(true));
                setAllMatchedEntitiesSelected(true);
              }}
              color="primary"
              variant="contained"
              autoFocus
            >
              Yes
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>


    </div>
  );
};

export default Sidebar;
