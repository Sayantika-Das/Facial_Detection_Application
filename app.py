import React, { useState, useRef, useEffect } from 'react';
import { Camera, Upload, Play, Pause, RotateCcw, Save } from 'lucide-react';

export default function FaceDetectionApp() {
  const [mode, setMode] = useState('upload');
  const [isDetecting, setIsDetecting] = useState(false);
  const [uploadedImage, setUploadedImage] = useState(null);
  const [detectionCount, setDetectionCount] = useState(0);
  const [scaleFactor, setScaleFactor] = useState(1.3);
  const [minNeighbors, setMinNeighbors] = useState(5);
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);
  const streamRef = useRef(null);
  const animationRef = useRef(null);

  useEffect(() => {
    return () => {
      stopWebcam();
    };
  }, []);

  const startWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480 } 
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;
      }
    } catch (err) {
      alert('Unable to access webcam: ' + err.message);
    }
  };

  const stopWebcam = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
  };

  const handleModeChange = (newMode) => {
    stopWebcam();
    setIsDetecting(false);
    setMode(newMode);
    setDetectionCount(0);
    
    if (newMode === 'webcam') {
      startWebcam();
    }
  };

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setUploadedImage(event.target.result);
        setDetectionCount(0);
      };
      reader.readAsDataURL(file);
    }
  };

  const detectFacesInImage = () => {
    if (!uploadedImage) return;

    const img = new Image();
    img.onload = () => {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);
      
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const faces = detectFaces(imageData, canvas.width, canvas.height);
      
      ctx.drawImage(img, 0, 0);
      faces.forEach(face => {
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 3;
        ctx.strokeRect(face.x, face.y, face.width, face.height);
      });
      
      setDetectionCount(faces.length);
    };
    img.src = uploadedImage;
  };

  const detectFacesInWebcam = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const video = videoRef.current;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const detect = () => {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const faces = detectFaces(imageData, canvas.width, canvas.height);
      
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      faces.forEach(face => {
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 3;
        ctx.strokeRect(face.x, face.y, face.width, face.height);
        
        ctx.fillStyle = '#00ff00';
        ctx.font = '16px Arial';
        ctx.fillText('Face', face.x, face.y - 5);
      });
      
      setDetectionCount(faces.length);
      
      if (isDetecting) {
        animationRef.current = requestAnimationFrame(detect);
      }
    };

    detect();
  };

  const toggleDetection = () => {
    if (mode === 'webcam') {
      if (!isDetecting) {
        setIsDetecting(true);
        detectFacesInWebcam();
      } else {
        setIsDetecting(false);
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
        }
      }
    } else {
      detectFacesInImage();
    }
  };

  const detectFaces = (imageData, width, height) => {
    const gray = convertToGrayscale(imageData);
    return simpleHaarLikeFaceDetection(gray, width, height, scaleFactor, minNeighbors);
  };

  const convertToGrayscale = (imageData) => {
    const data = imageData.data;
    const gray = new Uint8ClampedArray(data.length / 4);
    
    for (let i = 0; i < data.length; i += 4) {
      gray[i / 4] = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
    }
    
    return gray;
  };

  const simpleHaarLikeFaceDetection = (gray, width, height, scale, minN) => {
    const faces = [];
    const minSize = 30;
    const maxSize = Math.min(width, height) / 2;
    
    for (let size = minSize; size < maxSize; size = Math.floor(size * scale)) {
      for (let y = 0; y < height - size; y += Math.floor(size / 4)) {
        for (let x = 0; x < width - size; x += Math.floor(size / 4)) {
          if (isFaceRegion(gray, width, x, y, size)) {
            faces.push({ x, y, width: size, height: size });
          }
        }
      }
    }
    
    return mergeOverlappingFaces(faces, minN);
  };

  const isFaceRegion = (gray, width, x, y, size) => {
    const halfSize = Math.floor(size / 2);
    const quarterSize = Math.floor(size / 4);
    
    let topHalf = 0, bottomHalf = 0;
    let leftHalf = 0, rightHalf = 0;
    
    for (let dy = 0; dy < halfSize; dy++) {
      for (let dx = 0; dx < size; dx++) {
        const idx = (y + dy) * width + (x + dx);
        topHalf += gray[idx] || 0;
      }
    }
    
    for (let dy = halfSize; dy < size; dy++) {
      for (let dx = 0; dx < size; dx++) {
        const idx = (y + dy) * width + (x + dx);
        bottomHalf += gray[idx] || 0;
      }
    }
    
    for (let dy = 0; dy < size; dy++) {
      for (let dx = 0; dx < halfSize; dx++) {
        const idx = (y + dy) * width + (x + dx);
        leftHalf += gray[idx] || 0;
      }
    }
    
    for (let dy = 0; dy < size; dy++) {
      for (let dx = halfSize; dx < size; dx++) {
        const idx = (y + dy) * width + (x + dx);
        rightHalf += gray[idx] || 0;
      }
    }
    
    const totalPixels = size * size;
    const topAvg = topHalf / (halfSize * size);
    const bottomAvg = bottomHalf / (halfSize * size);
    const leftAvg = leftHalf / (size * halfSize);
    const rightAvg = rightHalf / (size * halfSize);
    
    return topAvg > bottomAvg * 0.9 && Math.abs(leftAvg - rightAvg) < 30;
  };

  const mergeOverlappingFaces = (faces, minNeighbors) => {
    if (faces.length === 0) return [];
    
    const merged = [];
    const used = new Array(faces.length).fill(false);
    
    for (let i = 0; i < faces.length; i++) {
      if (used[i]) continue;
      
      const cluster = [faces[i]];
      used[i] = true;
      
      for (let j = i + 1; j < faces.length; j++) {
        if (used[j]) continue;
        if (overlapRatio(faces[i], faces[j]) > 0.3) {
          cluster.push(faces[j]);
          used[j] = true;
        }
      }
      
      if (cluster.length >= Math.max(1, minNeighbors - 2)) {
        const avgFace = {
          x: Math.floor(cluster.reduce((sum, f) => sum + f.x, 0) / cluster.length),
          y: Math.floor(cluster.reduce((sum, f) => sum + f.y, 0) / cluster.length),
          width: Math.floor(cluster.reduce((sum, f) => sum + f.width, 0) / cluster.length),
          height: Math.floor(cluster.reduce((sum, f) => sum + f.height, 0) / cluster.length)
        };
        merged.push(avgFace);
      }
    }
    
    return merged;
  };

  const overlapRatio = (rect1, rect2) => {
    const x1 = Math.max(rect1.x, rect2.x);
    const y1 = Math.max(rect1.y, rect2.y);
    const x2 = Math.min(rect1.x + rect1.width, rect2.x + rect2.width);
    const y2 = Math.min(rect1.y + rect1.height, rect2.y + rect2.height);
    
    if (x2 < x1 || y2 < y1) return 0;
    
    const intersection = (x2 - x1) * (y2 - y1);
    const area1 = rect1.width * rect1.height;
    const area2 = rect2.width * rect2.height;
    
    return intersection / Math.min(area1, area2);
  };

  const resetCanvas = () => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    if (mode === 'upload' && uploadedImage) {
      const img = new Image();
      img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
      };
      img.src = uploadedImage;
    } else {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    
    setDetectionCount(0);
  };

  const saveImage = () => {
    const canvas = canvasRef.current;
    const link = document.createElement('a');
    link.download = 'face-detection-result.png';
    link.href = canvas.toDataURL();
    link.click();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2 flex items-center gap-3">
            <Camera className="text-indigo-600" size={40} />
            Face Detection App
          </h1>
          <p className="text-gray-600 mb-8">Detect faces in images or live webcam feed</p>

          {/* Mode Selection */}
          <div className="flex gap-4 mb-6">
            <button
              onClick={() => handleModeChange('upload')}
              className={`flex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition-all ${
                mode === 'upload'
                  ? 'bg-indigo-600 text-white shadow-lg'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              <Upload size={20} />
              Upload Image
            </button>
            <button
              onClick={() => handleModeChange('webcam')}
              className={`flex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition-all ${
                mode === 'webcam'
                  ? 'bg-indigo-600 text-white shadow-lg'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              <Camera size={20} />
              Live Webcam
            </button>
          </div>

          {/* Controls */}
          <div className="bg-gray-50 rounded-xl p-6 mb-6">
            <h3 className="font-semibold text-gray-700 mb-4">Detection Settings</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Scale Factor: {scaleFactor.toFixed(1)}
                </label>
                <input
                  type="range"
                  min="1.1"
                  max="2.0"
                  step="0.1"
                  value={scaleFactor}
                  onChange={(e) => setScaleFactor(parseFloat(e.target.value))}
                  className="w-full"
                />
                <p className="text-xs text-gray-500 mt-1">Higher = faster but less accurate</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Min Neighbors: {minNeighbors}
                </label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  step="1"
                  value={minNeighbors}
                  onChange={(e) => setMinNeighbors(parseInt(e.target.value))}
                  className="w-full"
                />
                <p className="text-xs text-gray-500 mt-1">Higher = fewer false positives</p>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              {mode === 'upload' && (
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                  <Upload size={18} />
                  Choose Image
                </button>
              )}
              
              <button
                onClick={toggleDetection}
                disabled={mode === 'upload' && !uploadedImage}
                className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {isDetecting ? <Pause size={18} /> : <Play size={18} />}
                {mode === 'webcam' ? (isDetecting ? 'Stop' : 'Start') : 'Detect Faces'}
              </button>
              
              <button
                onClick={resetCanvas}
                className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors"
              >
                <RotateCcw size={18} />
                Reset
              </button>
              
              <button
                onClick={saveImage}
                className="flex items-center gap-2 px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors"
              >
                <Save size={18} />
                Save Result
              </button>
            </div>
          </div>

          {/* Detection Count */}
          <div className="bg-indigo-50 border-2 border-indigo-200 rounded-xl p-4 mb-6">
            <p className="text-lg font-semibold text-indigo-800">
              Faces Detected: <span className="text-2xl">{detectionCount}</span>
            </p>
          </div>

          {/* Display Area */}
          <div className="bg-gray-900 rounded-xl p-4 flex items-center justify-center min-h-[400px]">
            {mode === 'webcam' && (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                className="hidden"
              />
            )}
            
            <canvas
              ref={canvasRef}
              className="max-w-full max-h-[600px] rounded-lg shadow-lg"
            />
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageUpload}
            className="hidden"
          />
        </div>
      </div>
    </div>
  );
}
