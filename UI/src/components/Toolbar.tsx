import React, { useState, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { GlobalContext } from '../GlobalState';
import axiosInstance from '../axiosSetup';
import {
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Checkbox,
  FormControlLabel,
  Button,
} from "@mui/material";
import HomeIcon from "@mui/icons-material/Home";
import RefreshIcon from "@mui/icons-material/Refresh";
import "../style/Toolbar.css";
import Tooltip from '@mui/material/Tooltip';
import { set } from "date-fns";

interface ToolbarProps {
  setPdfScaleValue: (value: number) => void;
  currentPage: number;
  totalPages: number;
  setIsActive: (active: boolean) => void;
}

const Toolbar = ({ setPdfScaleValue, currentPage, totalPages, setIsActive }: ToolbarProps) => {
  const globalContext = useContext(GlobalContext);

  if (!globalContext) {
    throw new Error("GlobalContext must be used within a GlobalProvider");
  }

  const { documentId, setBratOutput, setDocumentId, setFileName, setUpdateId } = globalContext;

  const [zoom, setZoom] = useState<number | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [runNERModel, setRunNERModel] = useState(true);
  const [runREModel, setRunREModel] = useState(false); // Only one can be active at a time
  const navigate = useNavigate();

  const zoomIn = () => {
    if (zoom) {
      if (zoom < 4) {
        setPdfScaleValue(zoom + 0.1);
        setZoom(zoom + 0.1);
      }
    } else {
      setPdfScaleValue(1);
      setZoom(1);
    }
  };

  const zoomOut = () => {
    if (zoom) {
      if (zoom > 0.2) {
        setPdfScaleValue(zoom - 0.1);
        setZoom(zoom - 0.1);
      }
    } else {
      setPdfScaleValue(1);
      setZoom(1);
    }
  };

  const goToHomePage = () => {
    navigate("/documents");
  };

  const handleReloadClick = () => {
    setIsDialogOpen(true);
  };

  const handleDialogClose = () => {
    setIsDialogOpen(false);
  };

  const handleDialogSubmit = async () => {
    setIsActive(true);
    
    let token = localStorage.getItem('accessToken');
    // Logic to handle the selected models
    if (runNERModel) {
      try {
        const response = await axiosInstance.get(`${import.meta.env.VITE_BACKEND_URL}/re-extract-all/${documentId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        setIsActive(false);
        setBratOutput(response.data.brat_format_output);
        setDocumentId(response.data.document_id);
        setUpdateId(response.data.update_id);
        setFileName(response.data.filename);
        navigate('/result', {
          state: {
            highlights: response.data.pdf_format_output,
            url: `${import.meta.env.VITE_PDF_BACKEND_URL}/statics/${response.data.filename}`
          }
        });
      } catch (error: any) {
        console.error('Error fetching document:', error);
      }
    } else if (runREModel) {
      try {
        const response = await axiosInstance.get(`${import.meta.env.VITE_BACKEND_URL}/re-extract-relations/${documentId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        setIsActive(false);
        setBratOutput(response.data.brat_format_output);
        setDocumentId(response.data.document_id);
        setUpdateId(response.data.update_id);
        setFileName(response.data.filename);
        navigate('/result', {
          state: {
            highlights: response.data.pdf_format_output,
            url: `${import.meta.env.VITE_PDF_BACKEND_URL}/statics/${response.data.filename}`
          }
        });
      } catch (error: any) {
        console.error('Error fetching document:', error);
      }
    }
    setIsDialogOpen(false);
  };

  // Ensure that only one checkbox is selected at a time
  const handleNERChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const isChecked = event.target.checked;
    setRunNERModel(isChecked);
    if (isChecked) {
      setRunREModel(false); // Disable RE if NER & RE is selected
    }
  };

  const handleREChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const isChecked = event.target.checked;
    setRunREModel(isChecked);
    if (isChecked) {
      setRunNERModel(false); // Disable NER & RE if RE is selected
    }
  };

  return (
    <div className="Toolbar">
        <Tooltip title="Click to back to the home page">
          <IconButton onClick={goToHomePage} className="HomeButton">
            <HomeIcon />
          </IconButton>
        </Tooltip>

      <div className="PageNumber">
        Page {currentPage} / {totalPages}
      </div>
      <div className="ZoomControls">
        <Tooltip title="Click to re run the NER & RE models">
          <IconButton onClick={handleReloadClick} className="ReloadButton">
            <RefreshIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Zoom out">
          <button onClick={zoomOut}>-</button>
        </Tooltip>
        <Tooltip title="Zoom in">
          <button onClick={zoomIn}>+</button>
        </Tooltip>
        {zoom ? `${(zoom * 100).toFixed(0)}%` : "Auto"}
      </div>

      <Dialog open={isDialogOpen} onClose={handleDialogClose}>
        <DialogTitle>Reload Options</DialogTitle>
        <DialogContent>
          <FormControlLabel
            control={
              <Checkbox
                checked={runNERModel}
                onChange={handleNERChange}
              />
            }
            label="Run NER & RE Models"
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={runREModel}
                onChange={handleREChange}
              />
            }
            label="Run RE Model"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogClose}>Cancel</Button>
          <Button onClick={handleDialogSubmit} color="primary">
            Submit
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default Toolbar;
