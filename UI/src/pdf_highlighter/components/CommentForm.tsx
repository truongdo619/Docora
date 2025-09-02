import React, { useEffect, useState } from "react";
import { CommentedHighlight } from "../types";
import CardActions from '@mui/material/CardActions';
import CardContent from '@mui/material/CardContent';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Slider from '@mui/material/Slider';
import Card from '@mui/material/Card';
import BratEmbedding from './BratEmbedding';
import DownloadIcon from '@mui/icons-material/Download';
import PolylineIcon from '@mui/icons-material/Polyline';
import { GlobalContext } from '../../../src/GlobalState';
import axiosInstance from '../../../src/axiosSetup';
import Divider from "@mui/material/Divider";
import CommentIcon from "@mui/icons-material/Comment";

function useWindowDimensions() {
  const [windowDimensions, setWindowDimensions] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  useEffect(() => {
    function handleResize() {
      setWindowDimensions({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    }

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return windowDimensions;
}

interface CommentFormProps {
  onSubmit: (input: string) => void;
  highlight: CommentedHighlight;
  brat_item: {
    text: string;
    entities: Array<any>;
    relations: Array<any>;
    selectedMode: string;
  };
  setCommentDialogData : (data: any) => void;
  toggleEditInProgress: (isEditing: boolean) => void;  
  pdfHighlighterUtils: any;
  onOpenTreeDialog?: () => void;
}



const CommentForm = ({
  onSubmit,
  highlight,
  brat_item,
  setCommentDialogData,
  toggleEditInProgress,
  pdfHighlighterUtils,
  onOpenTreeDialog
}: CommentFormProps) => {

  const globalContext = React.useContext(GlobalContext);
  if (!globalContext) {
    throw new Error("GlobalContext is undefined");
  }
  const { documentId, fileName, updateId } = globalContext;

  const [key, setKey] = useState(0);
  const [isVisible, setIsVisible] = useState(true);
  const [showAllEntities, setShowAllEntities] = useState(false);
  const { width: windowWidth } = useWindowDimensions();

  const calculateWidthBasedOnContent = (content: string) => {
    const baseWidth = 300; 
    const maxWidth = Math.min(1100, windowWidth - 20); 
    const contentWidth = content.length * 5; 
    return Math.min(baseWidth + contentWidth, maxWidth);
  };

  const baseCardWidth = calculateWidthBasedOnContent(brat_item.text);
  const cardWidth = showAllEntities 
    ? Math.min(baseCardWidth + 200, Math.min(1100, windowWidth - 20))
    : baseCardWidth;

  const isEvent = brat_item && "triggers" in brat_item;

  const svgStyle = {
    '& svg': {
      width: '100%',
      height: '16px',
      border: 'none',
    }
  };

  // Example method to handle JSON downloading (unchanged)

  function extractNumberFromParaId(para_id: string): number | null {
    const match = para_id.match(/\d+/);
    return match ? parseInt(match[0], 10) : null;
  }

  const handleDownload = async () => {
    let token = localStorage.getItem('accessToken');
    if (!showAllEntities) {
      try {
        const data = {
          document_id: documentId,
          update_id: updateId,
          id: highlight.id
        };
        const response = await axiosInstance.post(`${import.meta.env.VITE_BACKEND_URL}/download-entity/`, data, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        const jsonString = JSON.stringify(response.data, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName.split('.')[0] + `_output_${highlight.id}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        console.log('Download button clicked');
      } catch (error: any) {
        console.error('Error fetching document:', error);
      }
    } else {
      try {
        const para_id = extractNumberFromParaId(highlight.id.split('_')[0]);
        const data = {
          document_id: documentId,
          update_id: updateId,
          para_id: para_id
        };
        const response = await axiosInstance.post(`${import.meta.env.VITE_BACKEND_URL}/download-infor-para/`, data, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        const jsonString = JSON.stringify(response.data, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName.split('.')[0] + `_output_para${para_id}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        console.log('Download button clicked');
      } catch (error: any) {
        console.error('Error fetching document:', error);
      }
    }
  };

  useEffect(() => {
    setKey(prevKey => prevKey + 1);
  }, [brat_item]);

  if (!isVisible) {
    return null;
  }

  const handleClose = () => {
    setCommentDialogData(null);
    setIsVisible(false);
    toggleEditInProgress(false);
    if (pdfHighlighterUtils && pdfHighlighterUtils.scrolledToHighlightIdRef) {
      pdfHighlighterUtils.scrolledToHighlightIdRef.current = null;
      pdfHighlighterUtils.renderHighlightLayers();
    }
    // Reset URL hash
    const hash = document.location.hash;
    const parts = hash.split('#');
    document.location.hash = parts[0] + "#" + parts[1];
  };

  const toggleEntitiesView = () => {
    setShowAllEntities(prevState => !prevState);
    setKey(prevKey => prevKey + 1);
  };


  // Example: filter the brat_item so only highlight-related entities are shown
  const currentEntityId = highlight.id.split('_')[1];

  // console.log("currentEntityId", highlight);
  // console.log("brat_item", brat_item);
  const filteredBratItem = showAllEntities ? brat_item : (() => {

    if ("triggers" in brat_item) {
      // Filter triggers related to currentEntityId
      const filteredTriggers = brat_item.triggers?.filter(trigger =>
        trigger && trigger[0] === currentEntityId
      ) || [];

      // Filter events where event[1] matches currentEntityId
      const filteredEvents = brat_item.events?.filter(event =>
        event && event[1] === currentEntityId
      ) || [];

      // Collect related entity ids from event arguments + add currentEntityId itself
      const relatedEntityIds = new Set(["E" + currentEntityId]);
      filteredEvents.forEach(event => {
        if (event[2]) {
          event[2].forEach(([role, entityId]) => {
            relatedEntityIds.add(entityId);
          });
        }
      });

      // Filter entities to include currentEntityId + related entities from event arguments
      const filteredEntities = brat_item.entities?.filter(entity =>
        relatedEntityIds.has(entity[0])
      ) || [];

      return {
        ...brat_item,
        triggers: filteredTriggers,
        events: filteredEvents,
        entities: filteredEntities
      };
    }

    if (!brat_item || !brat_item.entities) return brat_item;

    const relatedEntityIds = new Set([currentEntityId]);
    if (brat_item.relations) {
      brat_item.relations.forEach(relation => {
        if (relation && relation[2]) {
          relation[2].forEach(([role, entityId]: [string, string]) => {
            if (entityId === currentEntityId) {
              relatedEntityIds.add(relation[2][0][1]);
              relatedEntityIds.add(relation[2][1][1]);
            }
          });
        }
      });
    }

    const filteredEntities = brat_item.entities.filter(entity => relatedEntityIds.has(entity[0]));
    const filteredRelations = brat_item.relations
      ? brat_item.relations.filter(r =>
          relatedEntityIds.has(r[2][0][1]) && relatedEntityIds.has(r[2][1][1])
        )
      : [];

    return { ...brat_item, entities: filteredEntities, relations: filteredRelations };
  })();

  return (
    <>
    <Box>
        <div>
          {/* <Card key={key} sx={{ minWidth: 300, width: cardWidth }}> */}
          <Card key={key} sx={{ minWidth: 300, width: "100%", boxShadow: 0 }}>
            <CardContent>
              <Typography variant="h5" component="div">
                {highlight.comment}
              </Typography>
              <Slider
                aria-label="Temperature"
                defaultValue={100}
                step={0}
                className={highlight.comment + '_COLOR'}
              />
              <Typography variant="body2">
                {'"' + highlight.content.text?.slice(0, 100) + '..."'}
              </Typography>
              <BratEmbedding docData={filteredBratItem} highlight={highlight} />
              
              {/* comment block */}
              <Divider sx={{ my: 2 }} />
              
              {highlight.user_comment && highlight.user_comment.length > 0 && (
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 1,
                    bgcolor: "#fafafa",
                    border: "1px solid #e0e0e0",
                    borderRadius: 1,
                    p: 1.5,
                  }}
                >
                  <CommentIcon fontSize="small" sx={{ mt: "2px" }} />
                  <Typography variant="body2" sx={{ whiteSpace: "pre-line" }}>
                    {highlight.user_comment}
                  </Typography>
                </Box>
              )}

            </CardContent>

            <CardActions sx={{ justifyContent: 'space-between' }}>
              <Box>
                <Button size="small" onClick={toggleEntitiesView}>
                  {showAllEntities
                  ? (isEvent ? "Show Only Highlighted Event" : "Show Only Highlighted Entity")
                  : (isEvent ? "Show All Events" : "Show All Entities")}
                </Button>
                <Button size="small" onClick={handleClose}>
                  Close
                </Button>
              </Box>

              <Box>
                <Button
                  sx={svgStyle}
                  size="small"
                  onClick={handleDownload}
                  startIcon={<DownloadIcon />}
                  variant="contained"
                  style={{ marginRight: '8px' }}
                >
                  Download JSON
                </Button>
                
                {brat_item.selectedMode !== "Paragraphs" && (
                  <Button
                    sx={svgStyle}
                    size="small"
                    startIcon={<PolylineIcon />}
                    variant="contained"
                    onClick={() => onOpenTreeDialog?.(highlight.id)}
                  >
                    Open Graph Visualization
                  </Button>
                )}
              </Box>
            </CardActions>
          </Card>
        </div>
    </Box>
    {/* The dialog for the tree visualization */}
    {/* <Dialog open={openTreeDialog} maxWidth="md" fullWidth> */}

    </>
  );
};

export default CommentForm;
