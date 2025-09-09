import React, { useContext, useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../axiosSetup';
import MUIDataTable, { MUIDataTableColumnDef } from "mui-datatables";
import Container from '@mui/material/Container';
import { GlobalContext } from '../GlobalState';
import LoadingOverlay from 'react-loading-overlay-ts';
import IconButton from '@mui/material/IconButton';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/GetApp';
import PrintIcon from '@mui/icons-material/Print';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import Box from '@mui/material/Box';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import { FileUploader } from 'react-drag-drop-files';
import Link from '@mui/material/Link';
import Tooltip from '@mui/material/Tooltip';
import { format, set } from 'date-fns';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Stack from '@mui/material/Stack';
import "../style/PDFUpload.css";
import { injectDynamicCSS } from '../injectStyles';
import defaultSettings from '../../settings.json';

// ─── New / Updated imports ───────────────────────────────────────────
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import DescriptionIcon from '@mui/icons-material/Description';
import PieChartIcon from '@mui/icons-material/PieChart';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

// ─── Constants ───────────────────────────────────────────────────────
const RAW_TYPES = ['PDF'];
const ANNOTATED_TYPES = ['PDF', 'JSON'];

interface DocumentData {
  id: string;
  filename: string;
  upload_time: string;
  pages: number;
  entities: number;
  relations: number;
  status: string;
  domain: string; // ← NEW
  task_id?: string;
  error?: string;
}

type BackendSettingsItem = { domain: string; setting: Record<string, any> };


const DocumentList: React.FC = () => {
  const globalContext = useContext(GlobalContext);

  if (!globalContext) {
    throw new Error("GlobalContext must be used within a GlobalProvider");
  }

  const {
    setBratOutput, setDocumentId, setFileName, setUpdateId,
    setDomainSettings, setSupportedDomains, setCurrentDomain, setSettings,
    domainSettings, supportedDomains
  } = globalContext;


  const navigate = useNavigate();
  const [isActive, setIsActive] = useState(false);
  const [tableData, setTableData] = useState<DocumentData[]>([]);
  const [openUploadDialog, setOpenUploadDialog] = useState(false);
  const [uploadOption, setUploadOption] = useState<'new' | 'annotated'>('new');   // NEW
  const [file, setFile] = useState<File | null>(null);
  const [notification, setNotification] = useState<string | null>(null); // Notification message
  const [notificationSeverity, setNotificationSeverity] = useState<'success' | 'error' | 'info'>('success');
  const [openSnackbar, setOpenSnackbar] = useState(false); // Snackbar visibility state
  const [dialogStep, setDialogStep] = useState<'select' | 'upload'>('select');
  // Keep the files until we have a matching pair
  const [annotatedPair, setAnnotatedPair] = useState<{ pdf?: File; json?: File }>({});

  // in component state:
  const [domain, setDomain] = useState<string>('');

  // Use a ref to store the interval ID
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchTableData = useCallback(async () => {
    setIsActive(true);
    let token = localStorage.getItem('accessToken');
    try {
      const response = await axiosInstance.post(
        `${import.meta.env.VITE_BACKEND_URL}/documents`,
        {},
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
          onUnauthorized: () => navigate('/'),
        }
      );

      setTableData(response.data.documents);


      // build domain -> settings map
      const settings = response.data.settings;
      if (Array.isArray(settings)) {
        const map = (settings as BackendSettingsItem[]).reduce<Record<string, any>>((acc, s) => {
          if (s?.domain) acc[s.domain] = s.setting || {};
          return acc;
        }, {});
        setDomainSettings(map);

        // inject CSS for ALL domains now
        settings.forEach((s: BackendSettingsItem) => {
          if (s?.setting) injectDynamicCSS(s.setting);
        });

        const domains = Object.keys(map);
        setSupportedDomains(domains);
        if (domains.length > 0) {
          setDomain(domains[0]); // Set the first domain
        }
      }

    } catch (error) {
      console.error('Error fetching document list:', error);
      if (error.response?.status === 401) {
        navigate('/signin');
      }
    } finally {
      setIsActive(false);
    }
  }, [navigate]);

  useEffect(() => {
    fetchTableData();
  }, [fetchTableData]);

  const pollPendingDocuments = useCallback(() => {
    const pendingDocuments = tableData.filter(
      (doc) => (doc.status === 'processing' || doc.status === 'queued') && doc.task_id
    );

    if (pendingDocuments.length > 0) {
      if (!pollingIntervalRef.current) {
        pollingIntervalRef.current = setInterval(async () => {
          let token = localStorage.getItem('accessToken');
          try {
            for (const doc of pendingDocuments) {
              const response = await axiosInstance.get(
                `${import.meta.env.VITE_BACKEND_URL}/task-status/${doc.task_id}/`,
                {
                  headers: {
                    'Authorization': `Bearer ${token}`,
                  },
                }
              );
              const { status } = response.data;

              if (status === 'completed') {
                const updatedDoc: DocumentData = {
                  ...response.data.result,
                  domain: doc.domain,
                  task_id: doc.task_id,
                };
                setTableData((prevData) =>
                  prevData.map((d) => (d.id === doc.id ? updatedDoc : d))
                );
                setNotification(`${doc.filename} has completed processing!`);
                setNotificationSeverity('success');
                setOpenSnackbar(true);
              } else if (status === 'failed') {
                setTableData((prevData) =>
                  prevData.map((d) =>
                    d.id === doc.id ? { ...d, status: 'failed', error: response.data.error } : d
                  )
                );
              }
            }
          } catch (error) {
            console.error('Error polling task status:', error);
          }
        }, 5000);
      }
    } else {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    }
  }, [tableData]);

  useEffect(() => {
    pollPendingDocuments();

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [pollPendingDocuments]);

  const handleCloseSnackbar = () => {
    setOpenSnackbar(false);
  };

  const handleFileNameClick = async (documentId: string, domain: string) => {
    setIsActive(true);
    let token = localStorage.getItem('accessToken');
    try {
      // Check if domain is undefined, set it to Polymer
      if (!domain) {domain = "polymer";}
      setCurrentDomain(domain);
      const domainCfg = domainSettings[domain];
      if (domainCfg) {
        setSettings((prev) => ({ ...prev, ...domainCfg }));
      }

      const response = await axiosInstance.post(
        `${import.meta.env.VITE_BACKEND_URL}/get-document/${documentId}`,
        {},
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
      navigate('/result', {
        state: {
          highlights: response.data.pdf_format_output,
          url: `${import.meta.env.VITE_PDF_BACKEND_URL}/statics/${response.data.filename}`,
        },
      });
    } catch (error: any) {
      console.error('Error fetching document:', error);
      setIsActive(false);
    }
  };

  const handleDeleteClick = async (id: string, fileName: string) => {
    const confirmDelete = window.confirm(`Are you sure you want to delete ${fileName}?`);
    if (!confirmDelete) return;

    setIsActive(true);
    let token = localStorage.getItem('accessToken');

    try {
      await axiosInstance.get(`${import.meta.env.VITE_BACKEND_URL}/delete-document/${id}`, {
        data: { fileName },
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      setTableData(tableData.filter((doc) => doc.id !== id));
    } catch (error: any) {
      console.error('Error deleting file:', error);
    } finally {
      setIsActive(false);
    }
  };

  const handleDownloadClick = async (document_id: string, fileName: string) => {
    const fileUrl = `${import.meta.env.VITE_BACKEND_URL}/download-document/${document_id}`;
    let token = localStorage.getItem('accessToken');

    try {
      const response = await axiosInstance.post(fileUrl, {}, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        responseType: 'blob',
      });

      // Create a download link for the file
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(new Blob([response.data]));
      link.setAttribute('download', fileName);

      // Append to the document body and trigger the download
      document.body.appendChild(link);
      link.click();

      // Clean up and remove the link
      link.parentNode?.removeChild(link);
    } catch (error) {
      console.error('Error downloading file:', error);
    }
  };

  const handlePrintClick = (fileName: string) => {
    const fileUrl = `${import.meta.env.VITE_PDF_BACKEND_URL}/statics/${fileName}`;
    const printWindow = window.open(fileUrl, '_blank');
    if (printWindow) {
      printWindow.onload = () => {
        printWindow.print();
      };
    }
  };

  // ─── Upload logic ─────────────────────────────────────────────────
  const handleUpload = async (input: File | File[] | FileList) => {
    const files: File[] =
      Array.isArray(input) ? input
      : input instanceof File   ? [input]
      : Array.from(input);

    if (!files.length) return;

    setIsActive(true);
    const token = localStorage.getItem('accessToken');

    try {
      if (uploadOption === 'new') {
        // ── original single-PDF flow (unchanged) ──
        for (const f of files) {
          const formData = new FormData();
          formData.append('file', f);
          formData.append('domain', domain);

          const res = await axiosInstance.post(
            `${import.meta.env.VITE_BACKEND_URL}/upload-pdf-queue/`,
            formData,
            { headers: { 'Content-Type': 'multipart/form-data', Authorization: `Bearer ${token}` } }
          );

          const newDoc: DocumentData = { ...res.data.infor, domain: domain, task_id: res.data.task_id };
          setTableData(prev => [...prev, newDoc]);
        }
      } else {
        // ── new annotated-pair flow ──
        // Expect exactly ONE pdf and ONE json
        const pdfFile  = files.find(f => f.type === 'application/pdf'          || f.name.toLowerCase().endsWith('.pdf'));
        const jsonFile = files.find(f => f.type === 'application/json'         || f.name.toLowerCase().endsWith('.json'));

        if (!pdfFile || !jsonFile) {
          setNotification('Select exactly one .pdf file and one .json file.');
          setNotificationSeverity('error');
          setOpenSnackbar(true);
          return;
        }

        const formData = new FormData();
        formData.append('pdf_file',  pdfFile);
        formData.append('json_file', jsonFile);
        
        const res = await axiosInstance.post(
          `${import.meta.env.VITE_BACKEND_URL}/upload-pdf-with-json/`,
          formData,
          { headers: { Authorization: `Bearer ${token}` }, maxBodyLength: Infinity }
        );

        const newDoc: DocumentData = { ...res.data.infor, domain: domain, task_id: res.data.task_id };
        setTableData(prev => [...prev, newDoc]);
      }
    } catch (e) {
      console.error('Error uploading file(s):', e);
      setNotification('Failed to upload document. Please try again.');
      setNotificationSeverity('error');
      setOpenSnackbar(true);
    } finally {
      setIsActive(false);
      setOpenUploadDialog(false);
      setDialogStep('select');
      setAnnotatedPair({}); // Reset the annotated pair state
    }
  };



  const columns: MUIDataTableColumnDef[] = [
    { name: "id", label: "ID" },
    {
      name: "filename",
      label: "File Name",
      options: {
        customBodyRender: (value: string, tableMeta) => {

          const status = tableMeta.rowData[6]; // Assuming status is at index 6
          if (status === 'queued') {
            return value;
          } else {
            return (
              <Link
                onClick={() => handleFileNameClick(tableMeta.rowData[0], tableMeta.rowData[7])}
                sx={{ cursor: 'pointer' }}
              >
                {value}
              </Link>
            );
          }
        },
      },
    },
    {
      name: "upload_time",
      label: "Uploaded Time",
      options: {
        customBodyRender: (value: string) => {
          try {
            // Convert the date to the desired time zone (UTC+9)
            const utcDate = new Date(value);
    
            // Adjust the time by adding 9 hours
            const utcPlusNineDate = new Date(utcDate.getTime() + 9 * 60 * 60 * 1000);
    
            // Format the date in a readable way
            const formattedDate = format(utcPlusNineDate, 'yyyy-MM-dd HH:mm:ss');
            return formattedDate;
          } catch (error) {
            console.error("Error formatting date:", error);
            // Return the fallback date-time "0000-00-00 00:00:00"
            return "0000-00-00 00:00:00";
          }
        },
      },
    },
    { name: "pages", label: "# Pages" },
    { name: "entities", label: "# Entities" },
    { name: "relations", label: "# Relations" },
    {
      name: "status",
      label: "Status",
      options: {
        customBodyRender: (value: string) => {
          if (value === 'queued') {
            return '⏳ Queued';
          } else if (value === 'processing') {
            return '🔄 Processing';
          } else if (value === 'completed') {
            return '✅ Completed';
          } else if (value === 'failed') {
            return '❌ Failed';
          }
          return value;
        },
      },
    },
    { name: "domain", label: "Domain" },
    {
      name: "actions",
      label: "Actions",
      options: {
        customBodyRender: (value: string, tableMeta) => {
          const id = tableMeta.rowData[0];
          const fileName = tableMeta.rowData[1];
          
          return (
            <>
              <Tooltip title="Download the original document">
                <IconButton aria-label="download" onClick={() => handleDownloadClick(id, fileName)}>
                  <DownloadIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Print the document">
                <IconButton aria-label="print" onClick={() => handlePrintClick(fileName)}>
                  <PrintIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Delete the selected document">
                <IconButton aria-label="delete" onClick={() => handleDeleteClick(id, fileName)}>
                  <DeleteIcon sx={{ color: 'indianred' }} />
                </IconButton>
              </Tooltip>
            </>
          );
        },
      },
    },
  ];

  const options = {
    filterType: 'checkbox',
    responsive: 'standard' as const,
    selectableRows: 'none' as const,
  };

  return (
    <LoadingOverlay
      active={isActive}
      spinner
      text='Processing ...'
      styles={{
        overlay: (base) => ({
          ...base,
          position: 'fixed',
          width: '100vw',
          height: '100vh',
          top: 0,
          left: 0,
          zIndex: 9999,
        }),
      }}
    >
      <Container
        className="document-list"
        maxWidth="xl"
        style={{ top: "150px", position: "relative" }}
      >
        <Box display="flex" justifyContent="flex-end" mb={2} style={{ marginBottom: 0 }}>
          <Button
            variant="contained"
            color="primary"
            onClick={() => setOpenUploadDialog(true)}
          >
            Upload Document
          </Button>
        </Box>
        <MUIDataTable
          title={"Document Management"}
          data={tableData}
          columns={columns}
          options={options}
          className="document-list-table"
        />
      </Container>

      <Snackbar
        open={openSnackbar}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={notificationSeverity}   // ← use the new state
          sx={{ width: '100%' }}
        >
          {notification}
        </Alert>
      </Snackbar>
      
      {/* Upload Dialog */}
      <Dialog open={openUploadDialog} onClose={() => { setOpenUploadDialog(false); setDialogStep('select'); }} fullWidth maxWidth='md'>
        <DialogTitle sx={{ textAlign: 'center', fontWeight: 600 }}>Upload Document</DialogTitle>
        <DialogContent sx={{mt: 2}}>





          {dialogStep === 'select' && (
            <Box sx={{
                mt: 1,
              }}>
                <Grid container spacing={4} justifyContent="center">
                  <Grid item xs={12} sm={6}>
                    <Paper
                      elevation={3}
                      sx={{ p: 4, textAlign: 'center', borderRadius: 3, cursor: 'pointer' }}
                      onClick={() => { setUploadOption('new'); setDialogStep('upload'); }}
                    >
                      <DescriptionIcon sx={{ fontSize: 60, mb: 2, color: '#2196f3' }} />
                      <Typography variant='subtitle1'>Upload New Document</Typography>
                      <Typography variant='body2' color='text.secondary'>
                        {"Extract and annotate a fresh PDF."}
                      </Typography>
                    </Paper>
                  </Grid>

                  {/* Upload Annotated */}
                  <Grid item xs={12} sm={6}>
                    <Paper
                      elevation={3}
                      sx={{ p: 4, textAlign: 'center', borderRadius: 3, cursor: 'pointer' }}
                      onClick={() => { setUploadOption('annotated'); setDialogStep('upload'); }}
                    >
                      <PieChartIcon sx={{ fontSize: 60, mb: 2, color: '#ffa726' }} />
                      <Typography variant='subtitle1'>Upload Annotated Document</Typography>
                      <Typography variant='body2' color='text.secondary'>
                        Continue working on an annotated PDF + JSON pair.
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>
            </Box>
            
            
          )}

          {dialogStep === 'upload' && (
            <>
              {/* Back button */}
              <Button startIcon={<ArrowBackIcon />} onClick={() => setDialogStep('select')} sx={{ mb: 2 }}>
                Choose another option
              </Button>

              {uploadOption === 'annotated' && (<Box sx={{ mb: 2, textAlign: 'center' }}>
                <Typography variant="body2" color="text.secondary">
                  {/* {uploadOption === 'new'
                    ? 'You can upload multiple PDF files at once.'
                    : 'Please ensure the PDF is uploaded first, followed by its JSON annotations.'} */}
                    {'Please ensure the PDF is uploaded first, followed by its JSON annotations.'}
                </Typography>
              </Box>)}

              { uploadOption === 'new' && (
                <Stack spacing={1} sx={{ mb: 1 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    <b>Step 1:</b> Select domain to annotate
                  </Typography>
                  <FormControl fullWidth size="small">
                    <InputLabel id="domain-select-label">Domain</InputLabel>
                    <Select
                      labelId="domain-select-label"
                      id="domain-select"
                      value={domain}
                      label="Domain"
                      onChange={(e) => setDomain(e.target.value as string)}
                    >
                      {supportedDomains.map((opt) => (
                        <MenuItem key={opt} value={opt}>
                          {opt.charAt(0).toUpperCase() + opt.slice(1)}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Stack>
              )}
                       
              { uploadOption === 'new' && (<Typography variant="subtitle2" color="text.secondary" sx={{ mt: 2, mb: 1 }}>
                  <b>Step 2:</b> Upload your PDF file(s) for annotation
                </Typography>
              )}

              <FileUploader
                handleChange={(input) => {
                  /* ───────────── NEW mode ───────────── */
                  if (uploadOption === 'new') {
                    handleUpload(input);                    // can be multi-select
                    return;
                  }

                  /* ────────── ANNOTATED mode ────────── */
                  const file = Array.isArray(input)
                    ? input[0]
                    : input instanceof File
                      ? input
                      : (input as FileList)[0];

                  const isPdf  = file.name.toLowerCase().endsWith('.pdf');
                  const isJson = file.name.toLowerCase().endsWith('.json');

                  /* Enforce order: PDF must come first */
                  setAnnotatedPair(prev => {
                    if (!prev.pdf && !isPdf) {
                      setNotification('Please upload the PDF first, then its JSON.');
                      setNotificationSeverity('error');
                      setOpenSnackbar(true);
                      return prev;                         // ignore out-of-order file
                    }
                    if (prev.pdf && isPdf) {
                      setNotification('PDF already selected. Now upload the corresponding JSON.');
                      setNotificationSeverity('info');
                      setOpenSnackbar(true);
                      return prev;
                    }

                    const next = { ...prev, [isPdf ? 'pdf' : 'json']: file };

                    /* When we have both, fire one request */
                    if (next.pdf && next.json) {
                      handleUpload([next.pdf, next.json]);
                      return {};                           // reset for the next pair
                    }
                    return next;
                  });
                }}
                name="file"
                types={uploadOption === 'new' ? RAW_TYPES : ANNOTATED_TYPES}
                multiple={uploadOption === 'new'}          // multi-select only in NEW
                classes="custom-fileUploader"
              />



            </>
          )}
        </DialogContent>
      </Dialog>
    </LoadingOverlay>
  );
};

export default DocumentList;
