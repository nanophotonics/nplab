function varargout = ThorlabsCameraGUI(varargin)
% THORLABSCAMERAGUI MATLAB code for ThorlabsCameraGUI.fig
%      THORLABSCAMERAGUI, by itself, creates a new THORLABSCAMERAGUI or raises the existing
%      singleton*.
%
%      H = THORLABSCAMERAGUI returns the handle to a new THORLABSCAMERAGUI or the handle to
%      the existing singleton*.
%
%      THORLABSCAMERAGUI('CALLBACK',hObject,eventData,handles,...) calls the local
%      function named CALLBACK in THORLABSCAMERAGUI.M with the given input arguments.
%
%      THORLABSCAMERAGUI('Property','Value',...) creates a new THORLABSCAMERAGUI or raises the
%      existing singleton*.  Starting from the left, property value pairs are
%      applied to the GUI before ThorlabsCameraGUI_OpeningFcn gets called.  An
%      unrecognized property name or invalid value makes property application
%      stop.  All inputs are passed to ThorlabsCameraGUI_OpeningFcn via varargin.
%
%      *See GUI Options on GUIDE's Tools menu.  Choose "GUI allows only one
%      instance to run (singleton)".
%
% See also: GUIDE, GUIDATA, GUIHANDLES

% Edit the above text to modify the response to help ThorlabsCameraGUI

% Last Modified by GUIDE v2.5 22-Jun-2018 09:57:54

% Begin initialization code - DO NOT EDIT
gui_Singleton = 1;
gui_State = struct('gui_Name',       mfilename, ...
                   'gui_Singleton',  gui_Singleton, ...
                   'gui_OpeningFcn', @ThorlabsCameraGUI_OpeningFcn, ...
                   'gui_OutputFcn',  @ThorlabsCameraGUI_OutputFcn, ...
                   'gui_LayoutFcn',  [] , ...
                   'gui_Callback',   []);
if nargin && ischar(varargin{1})
    gui_State.gui_Callback = str2func(varargin{1});
end

if nargout
    [varargout{1:nargout}] = gui_mainfcn(gui_State, varargin{:});
else
    gui_mainfcn(gui_State, varargin{:});
end
% End initialization code - DO NOT EDIT


% --- Executes just before ThorlabsCameraGUI is made visible.
function ThorlabsCameraGUI_OpeningFcn(hObject, eventdata, handles, varargin)
% This function has no output args, see OutputFcn.
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
% varargin   command line arguments to ThorlabsCameraGUI (see VARARGIN)

% Choose default command line output for ThorlabsCameraGUI
handles.output = hObject;

% Load TLCamera DotNet assembly. The assembly .dll is assumed to be in the 
% same folder as the scripts.
NET.addAssembly([pwd, '\Thorlabs.TSI.TLCamera.dll']);
disp('Dot NET assembly loaded.');

% Initialize TSISDK
handles.tlCameraSDK = Thorlabs.TSI.TLCamera.TLCameraSDK.OpenTLCameraSDK;

% Get serial numbers of connected TLCameras.
handles.serialNumbers = handles.tlCameraSDK.DiscoverAvailableCameras;
disp([num2str(handles.serialNumbers.Count), ' camera was discovered.']);
if (handles.serialNumbers.Count > 0)
    for iloop = 1:handles.serialNumbers.Count
        text{iloop} = char(handles.serialNumbers.Item(iloop-1));
    end
    set(handles.ButtonOpenCamera,'Enable','on');
    set(handles.ButtonCloseCamera,'Enable','off');
else
    text = {'No camera found'};
    set(handles.ButtonOpenCamera,'Enable','off');
    set(handles.ButtonCloseCamera,'Enable','off');
end
set(handles.PopUpSerialNumberList,'String',text);
set(handles.ButtonStartCamera,'Enable','off');
set(handles.ButtonStopCamera,'Enable','off');
set(findall(handles.PanelCameraSettings, '-property', 'Enable'), 'Enable', 'off')

% Update handles structure
guidata(hObject, handles);

% UIWAIT makes ThorlabsCameraGUI wait for user response (see UIRESUME)
% uiwait(handles.figure1);


% --- Outputs from this function are returned to the command line.
function varargout = ThorlabsCameraGUI_OutputFcn(hObject, eventdata, handles) 
% varargout  cell array for returning output args (see VARARGOUT);
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Get default command line output from handles structure
varargout{1} = handles.output;


% --- Executes on selection change in PopUpSerialNumberList.
function PopUpSerialNumberList_Callback(hObject, eventdata, handles)
% hObject    handle to PopUpSerialNumberList (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns PopUpSerialNumberList contents as cell array
%        contents{get(hObject,'Value')} returns selected item from PopUpSerialNumberList


% --- Executes during object creation, after setting all properties.
function PopUpSerialNumberList_CreateFcn(hObject, eventdata, handles)
% hObject    handle to PopUpSerialNumberList (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: popupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on button press in ButtonRefresh.
function ButtonRefresh_Callback(hObject, eventdata, handles)
% hObject    handle to ButtonRefresh (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

if (~isempty(handles.tlCameraSDK))
    handles.serialNumbers = handles.tlCameraSDK.DiscoverAvailableCameras;
    if (handles.serialNumbers.Count > 0)
        for iloop = 1:handles.serialNumbers.Count
            text{iloop} = char(handles.serialNumbers.Item(iloop-1));
        end
        set(handles.ButtonOpenCamera,'Enable','on');
        set(handles.ButtonCloseCamera,'Enable','off');
    else
        text = {'No camera found'};
        set(handles.ButtonOpenCamera,'Enable','off');
        set(handles.ButtonCloseCamera,'Enable','off');
    end
    set(handles.PopUpSerialNumberList,'String',text);
end

% Update handles structure
guidata(hObject, handles);

% --- Executes on button press in ButtonOpenCamera.
function ButtonOpenCamera_Callback(hObject, eventdata, handles)
% hObject    handle to ButtonOpenCamera (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

if (~isempty(handles.tlCameraSDK))
    contents = get(handles.PopUpSerialNumberList,'String');
    selectedSerial = contents{get(handles.PopUpSerialNumberList,'Value')};
    if (~strcmp(selectedSerial, 'No camera found'))
        % Open the camera with the selected serial number. 
        disp(['Opening camera ', selectedSerial])
        handles.tlCamera = handles.tlCameraSDK.OpenCamera(selectedSerial, false);
        
        % Get and Set camera parameters
        % Set camera dynamic settings
        handles.tlCamera.ExposureTime_us = uint32(str2double(get(handles.TextboxExposure_ms,'String'))*1000);
        
        % Check if the camera supports setting Gain.
        gainRange = handles.tlCamera.GainRange;
        if (gainRange.Maximum > 0)
            handles.tlCamera.Gain = uint32(str2double(get(handles.TextboxGain,'String')));
        else
            % Disable the Gain input if Gain is not supported
            set(handles.TextboxGain,'String','0');
            set(handles.TextboxGain,'Enable','Off'); 
        end
        % Check if the camera supports setting BlackLevel.
        blackLevelRange = handles.tlCamera.BlackLevelRange;
        if (blackLevelRange.Maximum > 0)
            handles.tlCamera.BlackLevel = uint32(str2double(get(handles.TextboxBlackLevel,'String')));
        else
            % Disable the Gain input if Gain is not supported
            set(handles.TextboxBlackLevel,'String','0');
            set(handles.TextboxBlackLevel,'Enable','Off'); 
        end
        % Get camera ROI and Bin settings
        roiAndBin = handles.tlCamera.ROIAndBin;
        set(handles.TextboxOriginX,'String',num2str(roiAndBin.ROIOriginX_pixels));
        set(handles.TextboxOriginY,'String',num2str(roiAndBin.ROIOriginY_pixels));
        set(handles.TextboxWidth,'String',num2str(roiAndBin.ROIWidth_pixels));
        set(handles.TextboxHeight,'String',num2str(roiAndBin.ROIHeight_pixels));
        set(handles.TextboxBinX,'String',num2str(roiAndBin.BinX));
        set(handles.TextboxBinY,'String',num2str(roiAndBin.BinY));
        maxWidth = int32(handles.tlCamera.SensorWidth_pixels) - int32(roiAndBin.ROIOriginX_pixels);
        set(handles.TextWidth,'String',['Width (Max: ' num2str(maxWidth) ')']);
        maxHeight = int32(handles.tlCamera.SensorHeight_pixels) - int32(roiAndBin.ROIOriginY_pixels);
        set(handles.TextHeight,'String',['Height (Max: ' num2str(maxHeight) ')']);
        
        % Check and set the data rate parameters
        text = {};
        if (handles.tlCamera.GetIsDataRateSupported(Thorlabs.TSI.TLCameraInterfaces.DataRate.ReadoutSpeed20MHz))
            % Scientific CCD cameras
            if (handles.tlCamera.GetIsDataRateSupported(Thorlabs.TSI.TLCameraInterfaces.DataRate.ReadoutSpeed40MHz))
                text = {'20 MHz', '40 MHz'};
            else
                text = {'20 MHz'};
            end
            set(handles.PopupReadoutSpeed,'String',text);
            handles.tlCamera.DataRate = Thorlabs.TSI.TLCameraInterfaces.DataRate.ReadoutSpeed20MHz;
        else
            if (handles.tlCamera.GetIsDataRateSupported(Thorlabs.TSI.TLCameraInterfaces.DataRate.FPS50))
                text = {'30 FPS', '50 FPS'};
            end
            if (~isempty(text))
                set(handles.PopupReadoutSpeed,'String',text);
                handles.tlCamera.DataRate = Thorlabs.TSI.TLCameraInterfaces.DataRate.FPS30;
            else
                set(handles.TextReadoutSpeed,'Visible','Off');
                set(handles.PopupReadoutSpeed,'Visible','Off');
            end
        end
        
        set(handles.PopupReadoutSpeed,'Value',1);
        
        if (handles.tlCamera.GetIsTapsSupported(Thorlabs.TSI.TLCameraInterfaces.Taps.QuadTap))
            text = {'1', '2', '4'};
        elseif (handles.tlCamera.GetIsTapsSupported(Thorlabs.TSI.TLCameraInterfaces.Taps.DualTap))
            text = {'1', '2'};
        elseif (handles.tlCamera.GetIsTapsSupported(Thorlabs.TSI.TLCameraInterfaces.Taps.SingleTap))
            text = {'1'};
        else
            set(handles.TextPopupTaps,'Visible','Off');
            set(handles.PopupTaps,'Visible','Off');
        end
        set(handles.PopupTaps,'String',text);

        if (handles.tlCamera.GetIsTapsSupported(Thorlabs.TSI.TLCameraInterfaces.Taps.SingleTap))
            handles.tlCamera.Taps = Thorlabs.TSI.TLCameraInterfaces.Taps.SingleTap;
            set(handles.PopupTaps,'Value',1);
        end
        
        if (handles.tlCamera.GainRange.Maximum <= 0)
            set(handles.TextboxGain,'Visible','Off')
            set(handles.TextGain,'Visible','Off')
        else
            set(handles.TextboxGain,'Visible','On')
            set(handles.TextGain,'Visible','On')
        end
        if (handles.tlCamera.BlackLevelRange.Maximum <= 0)
            set(handles.TextboxBlackLevel,'Visible','Off')
            set(handles.TextBlackLevel,'Visible','Off')
        else
            set(handles.TextboxBlackLevel,'Visible','On')
            set(handles.TextBlackLevel,'Visible','On')
        end
        
        % Set trigger states to radiosoftware trigger and continuous acquisition
        handles.tlCamera.FramesPerTrigger_zeroForUnlimited = 0;
        handles.tlCamera.OperationMode = Thorlabs.TSI.TLCameraInterfaces.OperationMode.SoftwareTriggered;
        set(handles.TextboxFramesPerTrigger,'String','Continuous');
        set(handles.PanelTriggerSettings,'SelectedObject',handles.RadioSoftware);
        handles.tlCamera.TriggerPolarity = Thorlabs.TSI.TLCameraInterfaces.TriggerPolarity.ActiveHigh;
        set(handles.PanelTriggerPolarity,'SelectedObject',handles.RadioOnHigh);
        handles.bitDepth = int32(handles.tlCamera.BitDepth);

        % Set enable states of controls
        set(handles.ButtonRefresh,'Enable','off');
        set(handles.ButtonOpenCamera,'Enable','off');
        set(handles.ButtonCloseCamera,'Enable','on');
        set(handles.ButtonStartCamera,'Enable','on');
        set(handles.ButtonStopCamera,'Enable','off');
        set(findall(handles.PanelCameraSettings, '-property', 'Enable'), 'Enable', 'on');

        % Check if the camera is Color
        handles.isColorCamera = handles.tlCamera.CameraSensorType == Thorlabs.TSI.TLCameraInterfaces.CameraSensorType.Bayer;

        if (handles.isColorCamera)
            % Disable panelbinning if camera is color
            set(findall(handles.PanelBinning,'-property', 'Enable'), 'Enable', 'off');
            % Enable color balance if camera is color
            set(findall(handles.PanelColorBalance,'-property', 'Enable'), 'Enable', 'on');
            text = {'sRGB','Linear sRGB','Unprocessed'};
            set(handles.PopupImageTypeSelection,'String',text);
            set(handles.PopupImageTypeSelection,'Value',1);
            
            % Load color processing .NET assemblies
            NET.addAssembly([pwd, '\Thorlabs.TSI.Demosaicker.dll']);
            NET.addAssembly([pwd, '\Thorlabs.TSI.ColorProcessor.dll']);
            
            % Initialize the demosaicker
            handles.demosaicker = Thorlabs.TSI.Demosaicker.Demosaicker;
            % Create color processor SDK.
            handles.colorProcessorSDK = Thorlabs.TSI.ColorProcessor.ColorProcessorSDK;
            
            % Query the default white balance matrix from camera. Alternatively
            % can also use user defined white balance matrix.
            handles.whiteBalanceMatrix = handles.tlCamera.GetDefaultWhiteBalanceMatrix;
            defaultWhiteBalanceMatrix = double(handles.whiteBalanceMatrix);
            % Update the color gain sliders with default values. 
            set(handles.SliderRedGain,'Value',defaultWhiteBalanceMatrix(1));
            set(handles.SliderGreenGain,'Value',defaultWhiteBalanceMatrix(5));
            set(handles.SliderBlueGain,'Value',defaultWhiteBalanceMatrix(9));
            set(handles.TextboxRedGain,'String',num2str(defaultWhiteBalanceMatrix(1)));
            set(handles.TextboxGreenGain,'String',num2str(defaultWhiteBalanceMatrix(5)));
            set(handles.TextboxBlueGain,'String',num2str(defaultWhiteBalanceMatrix(9)));

            % Query other relevant camera information
            handles.cameraColorCorrectionMatrix = handles.tlCamera.GetCameraColorCorrectionMatrix;
            handles.colorFilterArrayPhase = handles.tlCamera.ColorFilterArrayPhase;
            
            % Create standard RGB color processing pipeline.
            handles.standardRGBColorProcessor = handles.colorProcessorSDK.CreateStandardRGBColorProcessor(handles.whiteBalanceMatrix,...
                handles.cameraColorCorrectionMatrix, handles.bitDepth);
            % Create linear RGB color processing pipeline.
            handles.linearRGBColorProcessor = handles.colorProcessorSDK.CreateLinearRGBColorProcessor(handles.whiteBalanceMatrix,...
                handles.cameraColorCorrectionMatrix, handles.bitDepth);
        else
            % Enable panelbinning if camera is mono
            set(findall(handles.PanelBinning,'-property', 'Enable'), 'Enable', 'off');
            % Disable color balance if camera is mono
            set(findall(handles.PanelColorBalance,'-property', 'Enable'), 'Enable', 'off');
            text = {'Unprocessed'};
            set(handles.PopupImageTypeSelection,'String',text);
        end
    end
end

% Update handles structure
guidata(hObject, handles);

% --- Executes when user attempts to close figure1.
function figure1_CloseRequestFcn(hObject, eventdata, handles)
% hObject    handle to figure1 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

delete(handles.serialNumbers);

% Close TLCamera if opened
if (isfield(handles,'tlCamera'))
    if (~isempty(handles.tlCamera) && isvalid(handles.tlCamera))
        % if the camera is armed, stop the camera.
        if (handles.tlCamera.IsArmed)
            handles.tlCamera.Disarm;
        end
        handles.tlCamera.Dispose;
        delete(handles.tlCamera);
    end
end

% Close TLCameraSDK
if (~isempty(handles.tlCameraSDK))
    handles.tlCameraSDK.Dispose;
    delete(handles.tlCameraSDK);
end

% Close Color processor and SDK if opened
if (isfield(handles,'linearRGBColorProcessor'))
    if (~isempty(handles.linearRGBColorProcessor) && isvalid(handles.linearRGBColorProcessor))
        handles.linearRGBColorProcessor.Dispose;
        delete(handles.linearRGBColorProcessor);
    end
end
if (isfield(handles,'standardRGBColorProcessor'))
    if (~isempty(handles.standardRGBColorProcessor) && isvalid(handles.standardRGBColorProcessor))
        handles.standardRGBColorProcessor.Dispose;
        delete(handles.standardRGBColorProcessor);
    end
end
if (isfield(handles,'colorProcessorSDK'))
    if (~isempty(handles.colorProcessorSDK) && isvalid(handles.colorProcessorSDK))
        handles.colorProcessorSDK.Dispose;
        delete(handles.colorProcessorSDK);
    end
end

% Hint: delete(hObject) closes the figure
delete(hObject);


% --- Executes on button press in ButtonCloseCamera.
function ButtonCloseCamera_Callback(hObject, eventdata, handles)
% hObject    handle to ButtonCloseCamera (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Close TLCamera if opened
if (isfield(handles,'tlCamera'))
    if (~isempty(handles.tlCamera) && isvalid(handles.tlCamera))
        disp('Closing the camera');
        % if the camera is armed, stop the camera.
        if (handles.tlCamera.IsArmed)
            handles.tlCamera.Disarm;
        end
        handles.tlCamera.Dispose;
        delete(handles.tlCamera);
    end
end

set(handles.ButtonOpenCamera,'Enable','on');
set(handles.ButtonCloseCamera,'Enable','off');
set(handles.ButtonStartCamera,'Enable','off');
set(handles.ButtonStopCamera,'Enable','off');
set(findall(handles.PanelCameraSettings, '-property', 'Enable'), 'Enable', 'off')
set(handles.ButtonRefresh,'Enable','on');

% Close Color processor and SDK if opened
if (isfield(handles,'linearRGBColorProcessor'))
    if (~isempty(handles.linearRGBColorProcessor) && isvalid(handles.linearRGBColorProcessor))
        handles.linearRGBColorProcessor.Dispose;
        delete(handles.linearRGBColorProcessor);
    end
end
if (isfield(handles,'standardRGBColorProcessor'))
    if (~isempty(handles.standardRGBColorProcessor) && isvalid(handles.standardRGBColorProcessor))
        handles.standardRGBColorProcessor.Dispose;
        delete(handles.standardRGBColorProcessor);
    end
end
if (isfield(handles,'colorProcessorSDK'))
    if (~isempty(handles.colorProcessorSDK) && isvalid(handles.colorProcessorSDK))
        handles.colorProcessorSDK.Dispose;
        delete(handles.colorProcessorSDK);
    end
end

% Update handles structure
guidata(hObject, handles);


% --- Executes on button press in ButtonStartCamera.
function ButtonStartCamera_Callback(hObject, eventdata, handles)
% hObject    handle to ButtonStartCamera (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

disp('Starting the camera.');
set(handles.ButtonStartCamera,'Enable','off');
set(handles.ButtonStopCamera,'Enable','on');
set(findall(handles.PanelCameraSettings, '-property', 'Enable'), 'Enable', 'off')
set(findall(handles.PanelDynamicSettings, '-property', 'Enable'), 'Enable', 'on')
imageType = int32(get(handles.PopupImageTypeSelection,'Value'));

if (handles.isColorCamera)
    if (imageType < 3)
       set(findall(handles.PanelColorBalance,'-property', 'Enable'), 'Enable', 'on');
    end
end

data = get(handles.figure1, 'UserData');
data.stop = false;
set(handles.figure1, 'UserData',data);

% Arm and issue radiosoftware trigger if the camera is not in hardware trigger 
% mode.
handles.tlCamera.Arm;
if (handles.tlCamera.OperationMode ~= Thorlabs.TSI.TLCameraInterfaces.OperationMode.HardwareTriggered)
    handles.tlCamera.IssueSoftwareTrigger;
end

axes(handles.CameraImage)
maxPixelValue = double(2^handles.bitDepth - 1);

keepRunning = true;
while (keepRunning )
    % Check if image buffer has been filled
    if (isvalid(handles.tlCamera) && handles.tlCamera.NumberOfQueuedFrames > 0)
        imageFrame = handles.tlCamera.GetPendingFrameOrNull;
        if (~isempty(imageFrame))
            % For color images, the image data is in BGR format.
            imageData = imageFrame.ImageData.ImageData_monoOrBGR;
            
            disp(['Image frame number: ' num2str(imageFrame.FrameNumber)]);
            % TODO: custom image processing code goes here
            imageHeight = imageFrame.ImageData.Height_pixels;
            imageWidth = imageFrame.ImageData.Width_pixels;
            if (handles.isColorCamera && imageType < 3)
                % Allocate memory for demosaicking output.
                demosaickedImageData = NET.createArray('System.UInt16',imageHeight * imageWidth * 3);
                colorFormat = Thorlabs.TSI.ColorInterfaces.ColorFormat.BGRPixel;
                % Demosaic the Bayer patterned image from the camera.
                handles.demosaicker.Demosaic(imageWidth, imageHeight, int32(0), int32(0), handles.colorFilterArrayPhase,...
                    colorFormat, Thorlabs.TSI.ColorInterfaces.ColorSensorType.Bayer,...
                    handles.bitDepth, imageData, demosaickedImageData);
                
                % Allocate memory for color processed image.
                processedImageData = NET.createArray('System.UInt16',imageHeight * imageWidth * 3);
                if (imageType == 1)
                    % Use the standard RGB color processor to perform color transform.
                    handles.standardRGBColorProcessor.Transform48To48(demosaickedImageData, colorFormat,...
                    uint16(0), uint16(maxPixelValue), uint16(0), uint16(maxPixelValue),...
                    uint16(0), uint16(maxPixelValue), int32(0), int32(0), int32(0), processedImageData, colorFormat);
                else
                    % Use the linear RGB color processor to perform color transform.
                    handles.linearRGBColorProcessor.Transform48To48(demosaickedImageData, colorFormat,...
                    uint16(0), uint16(maxPixelValue), uint16(0), uint16(maxPixelValue),...
                    uint16(0), uint16(maxPixelValue), int32(0), int32(0), int32(0), processedImageData, colorFormat);
                end
                % Display the color image
                imageColor = reshape(uint16(processedImageData), [3, imageWidth, imageHeight]);
                imageColor = double(permute(imageColor,[3 2 1]));
                imageColor = flip(imageColor,3);    % Change from BGR to RGB
                image(imageColor/maxPixelValue), colorbar
            else
                imageData2D = reshape(uint16(imageData), [imageWidth, imageHeight]);
                imagesc(imageData2D'), colormap(gray), colorbar
            end
        end
        delete(imageFrame);
    end
    drawnow();
    if (isvalid(handles.figure1))
        userData = get(handles.figure1,'UserData');
        if userData.stop
            keepRunning = false;
        end
    end
end

% Stop the camera
if (isvalid(handles.tlCamera))
    disp('Stopping the camera');
    handles.tlCamera.Disarm;
    set(handles.ButtonStartCamera,'Enable','on');
    set(handles.ButtonStopCamera,'Enable','off');
    set(findall(handles.PanelCameraSettings, '-property', 'Enable'), 'Enable', 'on');
    if (handles.isColorCamera && imageType < 3)
        set(findall(handles.PanelBinning,'-property', 'Enable'), 'Enable', 'off');
    else
        set(findall(handles.PanelColorBalance,'-property', 'Enable'), 'Enable', 'off');
    end
end

if (isvalid(handles.figure1))
    % Update handles structure
    guidata(hObject, handles);
end


% --- Executes on button press in ButtonStopCamera.
function ButtonStopCamera_Callback(hObject, eventdata, handles)
% hObject    handle to ButtonStopCamera (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% handles.isStopCameraRequested = true;
data = get(handles.figure1, 'UserData');
data.stop = true;
set(handles.figure1, 'UserData',data);

% Update handles structure
guidata(hObject, handles);

function TextboxExposure_ms_Callback(hObject, eventdata, handles)
% hObject    handle to TextboxExposure_ms (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of TextboxExposure_ms as text
%        str2double(get(hObject,'String')) returns contents of TextboxExposure_ms as a double

exposureTime_ms = str2double(get(hObject,'String'));
% If the entry is valid, set camera exposure time
if (~isnan(exposureTime_ms))
    handles.tlCamera.ExposureTime_us = uint32(exposureTime_ms*1000);
else
    % Restore the field to camera value
    exposureTime_ms = handles.tlCamera.ExposureTime_us / 1000;
    set(hObject,'String',num2str(exposureTime_ms));
end
% Update handles structure
guidata(hObject, handles);

% --- Executes during object creation, after setting all properties.
function TextboxExposure_ms_CreateFcn(hObject, eventdata, handles)
% hObject    handle to TextboxExposure_ms (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function TextboxBlackLevel_Callback(hObject, eventdata, handles)
% hObject    handle to TextboxBlackLevel (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of TextboxBlackLevel as text
%        str2double(get(hObject,'String')) returns contents of TextboxBlackLevel as a double
blackLevelRange = handles.tlCamera.BlackLevelRange;
if (blackLevelRange.Maximum > 0)
    blackLevel = str2double(get(hObject,'String'));
    % If the entry is valid, set camera black level
    if (~isnan(blackLevel))
        % Check if the entry is within range.
        blackLevelRange = handles.tlCamera.BlackLevelRange;
        if (blackLevel > blackLevelRange.Maximum)
            blackLevel = blackLevelRange.Maximum;
            set(hObject,'String',num2str(blackLevel));
        else
            if (blackLevel < blackLevelRange.Minimum)
                blackLevel = blackLevelRange.Minimum;
                set(hObject,'String',num2str(blackLevel));
            end
        end
        handles.tlCamera.BlackLevel = uint32(blackLevel);
    else
        % Restore the field to camera value
        blackLevel = handles.tlCamera.BlackLevel;
        set(hObject,'String',num2str(blackLevel));
    end
end
% Update handles structure
guidata(hObject, handles);

% --- Executes during object creation, after setting all properties.
function TextboxBlackLevel_CreateFcn(hObject, eventdata, handles)
% hObject    handle to TextboxBlackLevel (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function TextboxGain_Callback(hObject, eventdata, handles)
% hObject    handle to TextboxGain (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of TextboxGain as text
%        str2double(get(hObject,'String')) returns contents of TextboxGain as a double

gainRange = handles.tlCamera.GainRange;
if (gainRange.Maximum > 0)
    gain = str2double(get(hObject,'String'));
    % If the entry is valid, set camera textboxgain
    if (~isnan(gain))
        % Check if the entry is within range.
        gainRange = handles.tlCamera.GainRange;
        if (gain > gainRange.Maximum)
            gain = gainRange.Maximum;
            set(hObject,'String',num2str(gain));
        else
            if (gain < gainRange.Minimum)
                gain = gainRange.Minimum;
                set(hObject,'String',num2str(gain));
            end
        end
        handles.tlCamera.Gain = uint32(gain);
    else
        % Restore the field to camera value
        gain = handles.tlCamera.Gain;
        set(hObject,'String',num2str(gain));
    end
end
% Update handles structure
guidata(hObject, handles);

% --- Executes during object creation, after setting all properties.
function TextboxGain_CreateFcn(hObject, eventdata, handles)
% hObject    handle to TextboxGain (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function TextboxBinX_Callback(hObject, eventdata, handles)
% hObject    handle to TextboxBinX (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of text7 as text
%        str2double(get(hObject,'String')) returns contents of text7 as a double
binX = str2double(get(hObject,'String'));
% If the entry is valid, set camera TextboxBinX
if (~isnan(binX))
    % Check if the entry is within range.
    binXRange = handles.tlCamera.BinXRange;
    if (binX > binXRange.Maximum)
        binX = binXRange.Maximum;
        set(hObject,'String',num2str(binX));
    else
        if (binX < binXRange.Minimum)
            binX = binXRange.Minimum;
            set(hObject,'String',num2str(binX));
        end
    end
    % Camera ROI and Bin needs to be set together. 
    roiAndBin = handles.tlCamera.ROIAndBin;
    roiAndBin.BinX = int32(binX);
    handles.tlCamera.ROIAndBin = roiAndBin;
else
    % Restore the field to camera value
    roiAndBin = handles.tlCamera.ROIAndBin;
    set(hObject,'String',num2str(roiAndBin.BinX));
end
% Update handles structure
guidata(hObject, handles);

% --- Executes during object creation, after setting all properties.
function TextboxBinX_CreateFcn(hObject, eventdata, handles)
% hObject    handle to TextboxBinX (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function TextboxBinY_Callback(hObject, eventdata, handles)
% hObject    handle to TextboxBinY (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of text8 as text
%        str2double(get(hObject,'String')) returns contents of text8 as a double
binY = str2double(get(hObject,'String'));
% If the entry is valid, set camera TextboxBinY
if (~isnan(binY))
    % Check if the entry is within range.
    binYRange = handles.tlCamera.BinYRange;
    if (binY > binYRange.Maximum)
        binY = binYRange.Maximum;
        set(hObject,'String',num2str(binY));
    else
        if (binY < binYRange.Minimum)
            binY = binYRange.Minimum;
            set(hObject,'String',num2str(binY));
        end
    end
    % Camera ROI and Bin needs to be set together. 
    roiAndBin = handles.tlCamera.ROIAndBin;
    roiAndBin.BinY = int32(binY);
    handles.tlCamera.ROIAndBin = roiAndBin;
else
    % Restore the field to camera value
    roiAndBin = handles.tlCamera.ROIAndBin;
    set(hObject,'String',num2str(roiAndBin.BinY));
end
% Update handles structure
guidata(hObject, handles);

% --- Executes during object creation, after setting all properties.
function TextboxBinY_CreateFcn(hObject, eventdata, handles)
% hObject    handle to TextboxBinY (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function TextboxOriginX_Callback(hObject, eventdata, handles)
% hObject    handle to TextboxOriginX (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of text5 as text
%        str2double(get(hObject,'String')) returns contents of text5 as a double
originX = str2double(get(hObject,'String'));
% If the entry is valid, set camera TextboxBinY
if (~isnan(originX))
    % Check if the entry is within range.
    roiAndBin = handles.tlCamera.ROIAndBin;
    if (originX > handles.tlCamera.SensorWidth_pixels - 1)
        originX = handles.tlCamera.SensorWidth_pixels - 1;
        set(hObject,'String',num2str(originX));
    else
        if (originX < 0)
            originX = 0;
            set(hObject,'String',num2str(originX));
        end
    end
    % Also check if the textboxwidth is now within range
    maxWidth = handles.tlCamera.SensorWidth_pixels - originX;
    % Update the TextboxWidth text
    set(handles.TextWidth,'String',['Width (Max: ' num2str(maxWidth) ')']);
    width = str2double(get(handles.TextboxWidth,'String'));
    if (width > maxWidth)
        width = maxWidth;
        set(handles.TextboxWidth,'String', num2str(width));
    end
    % Camera ROI and Bin needs to be set together. 
    roiAndBin.ROIOriginX_pixels = originX;
    roiAndBin.ROIWidth_pixels = width;
    handles.tlCamera.ROIAndBin = roiAndBin;
else
    % Restore the field to camera value
    roiAndBin = handles.tlCamera.ROIAndBin;
    set(hObject,'String',num2str(roiAndBin.ROIOriginX_pixels));
end
% Update handles structure
guidata(hObject, handles);


% --- Executes during object creation, after setting all properties.
function TextboxOriginX_CreateFcn(hObject, eventdata, handles)
% hObject    handle to TextboxOriginX (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function TextboxOriginY_Callback(hObject, eventdata, handles)
% hObject    handle to TextboxOriginY (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of text6 as text
%        str2double(get(hObject,'String')) returns contents of text6 as a double
originY = str2double(get(hObject,'String'));
% If the entry is valid, set camera TextboxBinY
if (~isnan(originY))
    % Check if the entry is within range.
    roiAndBin = handles.tlCamera.ROIAndBin;
    if (originY > handles.tlCamera.SensorHeight_pixels - 1)
        originY = handles.tlCamera.SensorHeight_pixels - 1;
        set(hObject,'String',num2str(originY));
    else
        if (originY < 0)
            originY = 0;
            set(hObject,'String',num2str(originY));
        end
    end
    % Also check if the textboxwidth is now within range
    maxHeight = handles.tlCamera.SensorHeight_pixels - originY;
    % Update the TextboxHeight text
    set(handles.TextHeight,'String',['Height (Max: ' num2str(maxHeight) ')']);
    height = str2double(get(handles.TextboxHeight,'String'));
    if (height > maxHeight)
        height = maxHeight;
        set(handles.TextboxHeight,'String', num2str(height));
    end
    % Camera ROI and Bin needs to be set together. 
    roiAndBin.ROIOriginY_pixels = originY;
    roiAndBin.ROIHeight_pixels = height;
    handles.tlCamera.ROIAndBin = roiAndBin;
else
    % Restore the field to camera value
    roiAndBin = handles.tlCamera.ROIAndBin;
    set(hObject,'String',num2str(roiAndBin.ROIOriginY_pixels));
end
% Update handles structure
guidata(hObject, handles);


% --- Executes during object creation, after setting all properties.
function TextboxOriginY_CreateFcn(hObject, eventdata, handles)
% hObject    handle to TextboxOriginY (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function TextboxWidth_Callback(hObject, eventdata, handles)
% hObject    handle to TextboxWidth (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of TextWidth as text
%        str2double(get(hObject,'String')) returns contents of TextWidth as a double
width = str2double(get(hObject,'String'));
% If the entry is valid, set camera TextboxBinY
if (~isnan(width))
    roiAndBin = handles.tlCamera.ROIAndBin;
    % Check if the entry is within range.
    maxWidth = int32(handles.tlCamera.SensorWidth_pixels) - int32(roiAndBin.ROIOriginX_pixels);
    % Update the TextboxWidth text
    set(handles.TextWidth,'String',['Width (Max: ' num2str(maxWidth) ')']);
    if (width > maxWidth)
        width = maxWidth;
        set(handles.TextboxWidth,'String', num2str(width));
    else
        if (width < 1)
            width = 1;
            set(handles.TextboxWidth,'String', num2str(width));
        end
    end
    % Camera ROI and Bin needs to be set together. 
    roiAndBin.ROIWidth_pixels = width;
    handles.tlCamera.ROIAndBin = roiAndBin;
else
    % Restore the field to camera value
    roiAndBin = handles.tlCamera.ROIAndBin;
    set(hObject,'String',num2str(roiAndBin.ROIWidth_pixels));
end
% Update handles structure
guidata(hObject, handles);


% --- Executes during object creation, after setting all properties.
function TextboxWidth_CreateFcn(hObject, eventdata, handles)
% hObject    handle to TextboxWidth (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function TextboxHeight_Callback(hObject, eventdata, handles)
% hObject    handle to TextboxHeight (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of TextHeight as text
%        str2double(get(hObject,'String')) returns contents of TextHeight as a double
height = str2double(get(hObject,'String'));
% If the entry is valid, set camera TextboxBinY
if (~isnan(height))
    roiAndBin = handles.tlCamera.ROIAndBin;
    % Check if the entry is within range.
    maxHeight = int32(handles.tlCamera.SensorHeight_pixels) - int32(roiAndBin.ROIOriginY_pixels);
    % Update the TextboxHeight text
    set(handles.TextHeight,'String',['Height (Max: ' num2str(maxHeight) ')']);
    if (height > maxHeight)
        height = maxHeight;
        set(handles.TextboxHeight,'String', num2str(height));
    else
        if (height < 1)
            height = 1;
            set(handles.TextboxHeight,'String', num2str(height));
        end
    end
    % Camera ROI and Bin needs to be set together. 
    roiAndBin.ROIHeight_pixels = height;
    handles.tlCamera.ROIAndBin = roiAndBin;
else
    % Restore the field to camera value
    roiAndBin = handles.tlCamera.ROIAndBin;
    set(hObject,'String',num2str(roiAndBin.ROIHeight_pixels));
end
% Update handles structure
guidata(hObject, handles);


% --- Executes during object creation, after setting all properties.
function TextboxHeight_CreateFcn(hObject, eventdata, handles)
% hObject    handle to TextboxHeight (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



% --- Executes on button press in ResetROI.
function ResetROI_Callback(hObject, eventdata, handles)
% hObject    handle to ResetROI (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
roiAndBin = handles.tlCamera.ROIAndBin;
roiAndBin.ROIOriginX_pixels = 0;
roiAndBin.ROIOriginY_pixels = 0;
roiAndBin.ROIWidth_pixels = handles.tlCamera.SensorWidth_pixels;
roiAndBin.ROIHeight_pixels = handles.tlCamera.SensorHeight_pixels;
handles.tlCamera.ROIAndBin = roiAndBin;
set(handles.TextboxOriginX,'String',num2str(roiAndBin.ROIOriginX_pixels));
set(handles.TextboxOriginY,'String',num2str(roiAndBin.ROIOriginY_pixels));
set(handles.TextboxWidth,'String',num2str(roiAndBin.ROIWidth_pixels));
set(handles.TextboxHeight,'String',num2str(roiAndBin.ROIHeight_pixels));
maxWidth = int32(handles.tlCamera.SensorWidth_pixels) - int32(roiAndBin.ROIOriginX_pixels);
set(handles.TextWidth,'String',['Width (Max: ' num2str(maxWidth) ')']);
maxHeight = int32(handles.tlCamera.SensorHeight_pixels) - int32(roiAndBin.ROIOriginY_pixels);
set(handles.TextHeight,'String',['Height (Max: ' num2str(maxHeight) ')']);


% --- Executes on selection change in PopupReadoutSpeed.
function PopupReadoutSpeed_Callback(hObject, eventdata, handles)
% hObject    handle to PopupReadoutSpeed (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns PopupReadoutSpeed contents as cell array
%        contents{get(hObject,'Value')} returns selected item from PopupReadoutSpeed
contents = cellstr(get(hObject,'String'));
selectedContent = contents{get(hObject,'Value')};
switch selectedContent
    case '20 MHz'
        handles.TLCamera.DataRate = Thorlabs.TSI.TLCameraInterfaces.DataRate.ReadoutSpeed20MHz;
    case '40 MHz'
        handles.TLCamera.DataRate = Thorlabs.TSI.TLCameraInterfaces.DataRate.ReadoutSpeed40MHz;
end


% --- Executes during object creation, after setting all properties.
function PopupReadoutSpeed_CreateFcn(hObject, eventdata, handles)
% hObject    handle to PopupReadoutSpeed (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: popupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on selection change in PopupTaps.
function PopupTaps_Callback(hObject, eventdata, handles)
% hObject    handle to PopupTaps (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns PopupTaps contents as cell array
%        contents{get(hObject,'Value')} returns selected item from PopupTaps
tapsIndex = uint32(get(hObject,'Value') - 1);
switch (tapsIndex)
    case 0
        taps = Thorlabs.TSI.TLCameraInterfaces.Taps.SingleTap;
    case 1
        taps = Thorlabs.TSI.TLCameraInterfaces.Taps.DualTap;
    case 2
        taps = Thorlabs.TSI.TLCameraInterfaces.Taps.QuadTap;
end
if (handles.tlCamera.GetIsTapsSupported(taps))
    handles.tlCamera.Taps = taps;
end

% --- Executes during object creation, after setting all properties.
function PopupTaps_CreateFcn(hObject, eventdata, handles)
% hObject    handle to PopupTaps (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: popupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on slider movement.
function SliderRedGain_Callback(hObject, eventdata, handles)
% hObject    handle to SliderRedGain (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'Value') returns position of slider
%        get(hObject,'Min') and get(hObject,'Max') to determine range of slider
% Update TextboxRedGain
set(handles.TextboxRedGain,'String',num2str(get(hObject,'Value')));
% Update camera color matrix
imageType = int32(get(handles.PopupImageTypeSelection,'Value'));
UpdateWhiteBalanceMatrix(imageType, handles);


% --- Executes during object creation, after setting all properties.
function SliderRedGain_CreateFcn(hObject, eventdata, handles)
% hObject    handle to SliderRedGain (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: slider controls usually have a light gray background.
if isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor',[.9 .9 .9]);
end


% --- Executes on slider movement.
function SliderGreenGain_Callback(hObject, eventdata, handles)
% hObject    handle to SliderGreenGain (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'Value') returns position of slider
%        get(hObject,'Min') and get(hObject,'Max') to determine range of slider
% Update TextboxGreenGain
set(handles.TextboxGreenGain,'String',num2str(get(hObject,'Value')));
% Update camera color matrix
imageType = int32(get(handles.PopupImageTypeSelection,'Value'));
UpdateWhiteBalanceMatrix(imageType, handles);


% --- Executes during object creation, after setting all properties.
function SliderGreenGain_CreateFcn(hObject, eventdata, handles)
% hObject    handle to SliderGreenGain (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: slider controls usually have a light gray background.
if isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor',[.9 .9 .9]);
end


% --- Executes on slider movement.
function SliderBlueGain_Callback(hObject, eventdata, handles)
% hObject    handle to SliderBlueGain (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'Value') returns position of slider
%        get(hObject,'Min') and get(hObject,'Max') to determine range of slider
% Update TextboxBlueGain
set(handles.TextboxBlueGain,'String',num2str(get(hObject,'Value')));
% Update camera color matrix
imageType = int32(get(handles.PopupImageTypeSelection,'Value'));
UpdateWhiteBalanceMatrix(imageType, handles);


% --- Executes during object creation, after setting all properties.
function SliderBlueGain_CreateFcn(hObject, eventdata, handles)
% hObject    handle to SliderBlueGain (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: slider controls usually have a light gray background.
if isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor',[.9 .9 .9]);
end



function TextboxFramesPerTrigger_Callback(hObject, eventdata, handles)
% hObject    handle to TextboxFramesPerTrigger (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of TextboxFramesPerTrigger as text
%        str2double(get(hObject,'String')) returns contents of TextboxFramesPerTrigger as a double
framesPerTrigger = uint32(str2double(get(hObject,'String')));
if (~isnan(framesPerTrigger))
    handles.tlCamera.FramesPerTrigger_zeroForUnlimited = framesPerTrigger;
    if (framesPerTrigger == 0)
        set(handles.TextboxFramesPerTrigger,'String','Continuous');
    end
else
    handles.tlCamera.FramesPerTrigger_zeroForUnlimited = 0;
    set(handles.TextboxFramesPerTrigger,'String','Continuous');
end


% --- Executes during object creation, after setting all properties.
function TextboxFramesPerTrigger_CreateFcn(hObject, eventdata, handles)
% hObject    handle to TextboxFramesPerTrigger (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


function TextboxRedGain_Callback(hObject, eventdata, handles)
% hObject    handle to TextboxRedGain (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of TextboxRedGain as text
%        str2double(get(hObject,'String')) returns contents of TextboxRedGain as a double
redGain = str2double(get(hObject,'String'));
% If the entry is valid, set camera black level
if (~isnan(redGain))
    % Check if the entry is within range.
    if (redGain > handles.SliderRedGain.Max)
        redGain = handles.SliderRedGain.Max;
        set(hObject,'String',num2str(redGain));
    else
        if (redGain < handles.SliderRedGain.Min)
            redGain = handles.SliderRedGain.Min;
            set(hObject,'String',num2str(redGain));
        end
    end
    set(handles.SliderRedGain,'Value',redGain);
else
    % Restore the field to slider value
    redGain = get(handles.SliderRedGain,'Value');
    set(hObject,'String',num2str(redGain));
end
% Update camera color matrix
imageType = int32(get(handles.PopupImageTypeSelection,'Value'));
UpdateWhiteBalanceMatrix(imageType, handles);


% --- Executes during object creation, after setting all properties.
function TextboxRedGain_CreateFcn(hObject, eventdata, handles)
% hObject    handle to TextboxRedGain (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function TextboxGreenGain_Callback(hObject, eventdata, handles)
% hObject    handle to TextboxGreenGain (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of TextboxGreenGain as text
%        str2double(get(hObject,'String')) returns contents of TextboxGreenGain as a double
greenGain = str2double(get(hObject,'String'));
% If the entry is valid, set camera black level
if (~isnan(greenGain))
    % Check if the entry is within range.
    if (greenGain > handles.SliderGreenGain.Max)
        greenGain = handles.SliderGreenGain.Max;
        set(hObject,'String',num2str(greenGain));
    else
        if (greenGain < handles.SliderGreenGain.Min)
            greenGain = handles.SliderGreenGain.Min;
            set(hObject,'String',num2str(greenGain));
        end
    end
    set(handles.SliderGreenGain,'Value',greenGain);
else
    % Restore the field to slider value
    greenGain = get(handles.SliderGreenGain,'Value');
    set(hObject,'String',num2str(greenGain));
end
% Update camera color matrix
imageType = int32(get(handles.PopupImageTypeSelection,'Value'));
UpdateWhiteBalanceMatrix(imageType, handles);



% --- Executes during object creation, after setting all properties.
function TextboxGreenGain_CreateFcn(hObject, eventdata, handles)
% hObject    handle to TextboxGreenGain (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function TextboxBlueGain_Callback(hObject, eventdata, handles)
% hObject    handle to TextboxBlueGain (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of TextboxBlueGain as text
%        str2double(get(hObject,'String')) returns contents of TextboxBlueGain as a double
blueGain = str2double(get(hObject,'String'));
% If the entry is valid, set camera black level
if (~isnan(blueGain))
    % Check if the entry is within range.
    if (blueGain > handles.SliderBlueGain.Max)
        blueGain = handles.SliderBlueGain.Max;
        set(hObject,'String',num2str(blueGain));
    else
        if (blueGain < handles.SliderBlueGain.Min)
            blueGain = handles.SliderBlueGain.Min;
            set(hObject,'String',num2str(blueGain));
        end
    end
    set(handles.SliderBlueGain,'Value',blueGain);
else
    % Restore the field to slider value
    blueGain = get(handles.SliderBlueGain,'Value');
    set(hObject,'String',num2str(blueGain));
end
% Update camera color matrix
imageType = int32(get(handles.PopupImageTypeSelection,'Value'));
UpdateWhiteBalanceMatrix(imageType, handles);



% --- Executes during object creation, after setting all properties.
function TextboxBlueGain_CreateFcn(hObject, eventdata, handles)
% hObject    handle to TextboxBlueGain (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on selection change in PopupImageTypeSelection.
function PopupImageTypeSelection_Callback(hObject, eventdata, handles)
% hObject    handle to PopupImageTypeSelection (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns PopupImageTypeSelection contents as cell array
%        contents{get(hObject,'Value')} returns selected item from PopupImageTypeSelection
imageType = int32(get(hObject,'Value'));
UpdateWhiteBalanceMatrix(imageType, handles);
        
% --- Executes during object creation, after setting all properties.
function PopupImageTypeSelection_CreateFcn(hObject, eventdata, handles)
% hObject    handle to PopupImageTypeSelection (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: popupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes when selected object is changed in PanelTriggerSettings.
function PanelTriggerSettings_SelectionChangedFcn(hObject, eventdata, handles)
% hObject    handle to the selected object in PanelTriggerSettings 
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
switch hObject
    case handles.RadioSoftware
        handles.tlCamera.OperationMode = Thorlabs.TSI.TLCameraInterfaces.OperationMode.SoftwareTriggered;
    case handles.RadioHardwareStandard
        handles.tlCamera.OperationMode = Thorlabs.TSI.TLCameraInterfaces.OperationMode.HardwareTriggered;
    case handles.RadioHardwarePDX
        handles.tlCamera.OperationMode = Thorlabs.TSI.TLCameraInterfaces.OperationMode.Bulb;
end
    


% --- Executes when selected object is changed in PanelTriggerPolarity.
function PanelTriggerPolarity_SelectionChangedFcn(hObject, eventdata, handles)
% hObject    handle to the selected object in PanelTriggerPolarity 
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
switch hObject
    case handles.RadioOnHigh
        handles.tlCamera.TriggerPolarity = Thorlabs.TSI.TLCameraInterfaces.TriggerPolarity.ActiveHigh;
    case handles.RadioOnLow
        handles.tlCamera.TriggerPolarity = Thorlabs.TSI.TLCameraInterfaces.TriggerPolarity.ActiveLow;
end


% Update the white balance matrix in color processor.
function UpdateWhiteBalanceMatrix(imageType, handles)
handles.whiteBalanceMatrix(1) = get(handles.SliderRedGain,'Value');
handles.whiteBalanceMatrix(5) = get(handles.SliderGreenGain,'Value');
handles.whiteBalanceMatrix(9) = get(handles.SliderBlueGain,'Value');

if (isfield(handles,'standardRGBColorProcessor') && isfield(handles,'linearRGBColorProcessor') ...
        && ~isempty(handles.standardRGBColorProcessor) && ~isempty(handles.linearRGBColorProcessor) ...
        && isvalid(handles.standardRGBColorProcessor) && isvalid(handles.linearRGBColorProcessor))
    % Update the white balance matrices
    handles.standardRGBColorProcessor.ClearColorTransformMatrices;
    handles.standardRGBColorProcessor.InsertColorTransformMatrix(0, handles.whiteBalanceMatrix);
    handles.standardRGBColorProcessor.InsertColorTransformMatrix(1, handles.cameraColorCorrectionMatrix);
    handles.linearRGBColorProcessor.ClearColorTransformMatrices;
    handles.linearRGBColorProcessor.InsertColorTransformMatrix(0, handles.whiteBalanceMatrix);
    handles.linearRGBColorProcessor.InsertColorTransformMatrix(1, handles.cameraColorCorrectionMatrix);
end

% Update the GUI states
if (handles.isColorCamera)
    switch imageType
        case 1
            set(findall(handles.PanelBinning,'-property', 'Enable'), 'Enable', 'off');
            set(findall(handles.PanelColorBalance,'-property', 'Enable'), 'Enable', 'on');
        case 2
            set(findall(handles.PanelBinning,'-property', 'Enable'), 'Enable', 'off');
            set(findall(handles.PanelColorBalance,'-property', 'Enable'), 'Enable', 'on');
        case 3
            set(findall(handles.PanelBinning,'-property', 'Enable'), 'Enable', 'on');
            set(findall(handles.PanelColorBalance,'-property', 'Enable'), 'Enable', 'off');
    end
end
