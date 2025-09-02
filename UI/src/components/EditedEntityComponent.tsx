import React, { useState, useEffect, useRef } from 'react';
import { Typography, Box } from '@mui/material';

interface HighlightedParagraphProps {
  text: string;
  onTextChange: (newText: string) => void;
  onSelectionChange: (start: number, end: number) => void;
  defaultStart?: number;
  defaultEnd?: number;
  entityType?: string;
}


const EditedEntityComponent: React.FC<HighlightedParagraphProps> = ({
  text,
  onTextChange,
  onSelectionChange,
  defaultStart = 0,
  defaultEnd = 0,
  entityType = 'default',
}) => {
  const [content, setContent] = useState<string>(text);
  const [selectionStart, setSelectionStart] = useState<number>(defaultStart);
  const [selectionEnd, setSelectionEnd] = useState<number>(defaultEnd);
  const [isSelecting, setIsSelecting] = useState<boolean>(false);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setContent(text);
    setSelectionStart(defaultStart);
    setSelectionEnd(defaultEnd);
  }, [text, defaultStart, defaultEnd]);

  const handleSelectionChange = () => {
    if (!isSelecting || !contentRef.current) return;

    const selection = window.getSelection();
    if (selection && selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      const preCaretRange = range.cloneRange();
      preCaretRange.selectNodeContents(contentRef.current);
      preCaretRange.setEnd(range.startContainer, range.startOffset);
      const start = preCaretRange.toString().length;

      const postCaretRange = range.cloneRange();
      postCaretRange.selectNodeContents(contentRef.current);
      postCaretRange.setEnd(range.endContainer, range.endOffset);
      const end = postCaretRange.toString().length;

      setSelectionStart(start);
      setSelectionEnd(end);
      onSelectionChange(start, end);
      setIsSelecting(false);
    }
  };

  const enableSelectionMode = () => {
    setIsSelecting(true);
  };

  return (
    <div>
      <Box 
        sx={{ 
          border: '1px solid #c4c4c4', 
          borderRadius: '4px', 
          padding: '16px', 
          position: 'relative', 
          marginBottom: '8px',
          '&:hover': {
            borderColor: 'black',
          },
          '&:focus-within': {
            borderColor: 'black',
          },
          marginTop: '16px'
        }}
        onClick={enableSelectionMode}
      >
        <Typography 
          variant="caption" 
          sx={{ 
            position: 'absolute', 
            top: '-10px', 
            left: '10px', 
            backgroundColor: 'white', 
            padding: '0 4px'
          }}
        >
          Span Text
        </Typography>
        <Typography variant="body1">
          <div
            ref={contentRef}
            style={{ backgroundColor: 'transparent', outline: 'none', userSelect: 'text' }}
            onMouseUp={handleSelectionChange}
            onClick={enableSelectionMode}
          >
            {content.slice(0, selectionStart)}
            <span className={entityType}>{content.slice(selectionStart, selectionEnd)}</span>
            {content.slice(selectionEnd)}
          </div>
        </Typography>
      </Box>
      <Typography 
        variant="body2" 
        sx={{ 
          marginTop: '8px',  
        }}
      >
        Selected Span: "<b>{content.slice(selectionStart, selectionEnd)}</b>"
      </Typography>
    </div>
  );
};

export default EditedEntityComponent;
