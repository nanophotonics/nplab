using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using System.Windows.Threading;
using Thorlabs.TSI.ColorInterfaces;
using Thorlabs.TSI.ColorProcessor;
using Thorlabs.TSI.Core;
using Thorlabs.TSI.CoreInterfaces;
using Thorlabs.TSI.Demosaicker;
using Thorlabs.TSI.ImageData;
using Thorlabs.TSI.ImageDataInterfaces;
using Thorlabs.TSI.TLCamera;
using Thorlabs.TSI.TLCameraInterfaces;

namespace Example_DotNet_Camera_Interface
{
    public partial class Form1 : Form
    {
        private readonly DispatcherTimer _dispatcherTimerUpdateUI = new DispatcherTimer();

        private Bitmap _latestDisplayBitmap;
        private ITLCameraSDK _tlCameraSDK;
        private ITLCamera _tlCamera;

        private ushort[] _demosaickedData = null;
        private ushort[] _processedImage = null;
        private Demosaicker _demosaicker = new Demosaicker();
        private ColorFilterArrayPhase _colorFilterArrayPhase;
        private ColorProcessor _colorProcessor = null;
        private bool _isColor = false;
        private ColorProcessorSDK _colorProcessorSDK = null;

        public Form1()
        {
            this.InitializeComponent();

            this._tlCameraSDK = TLCameraSDK.OpenTLCameraSDK();
            var serialNumbers = this._tlCameraSDK.DiscoverAvailableCameras();

            if (serialNumbers.Count > 0)
            {
                this._tlCamera = this._tlCameraSDK.OpenCamera(serialNumbers.First(), false);

                this._tlCamera.ExposureTime_us = 50000;
                if (this._tlCamera.GainRange.Maximum > 0)
                {
                    const double gainDb = 6.0;
                    var gainIndex = this._tlCamera.ConvertDecibelsToGain(gainDb);
                    this._tlCamera.Gain = gainIndex;
                }
                if (this._tlCamera.BlackLevelRange.Maximum > 0)
                {
                    this._tlCamera.BlackLevel = 48;
                }

                this._isColor = this._tlCamera.CameraSensorType == CameraSensorType.Bayer;
                if (this._isColor)
                {
                    this._colorProcessorSDK = new ColorProcessorSDK();
                    this._colorFilterArrayPhase = this._tlCamera.ColorFilterArrayPhase;
                    var colorCorrectionMatrix = this._tlCamera.GetCameraColorCorrectionMatrix();
                    var whiteBalanceMatrix = this._tlCamera.GetDefaultWhiteBalanceMatrix();
                    this._colorProcessor = (ColorProcessor)this._colorProcessorSDK.CreateStandardRGBColorProcessor(whiteBalanceMatrix, colorCorrectionMatrix, (int)this._tlCamera.BitDepth);
                }

                this._tlCamera.OperationMode = OperationMode.SoftwareTriggered;

                this._tlCamera.Arm();

                this._tlCamera.IssueSoftwareTrigger();

                this._dispatcherTimerUpdateUI.Interval = TimeSpan.FromMilliseconds(50);
                this._dispatcherTimerUpdateUI.Tick += this.DispatcherTimerUpdateUI_Tick;
                this._dispatcherTimerUpdateUI.Start();
            }
            else
            {
                MessageBox.Show("No Thorlabs camera detected.");
            }
        }

        protected override void OnClosing(CancelEventArgs e)
        {
            base.OnClosing(e);

            if (this._dispatcherTimerUpdateUI != null)
            {
                this._dispatcherTimerUpdateUI.Stop();
                this._dispatcherTimerUpdateUI.Tick -= this.DispatcherTimerUpdateUI_Tick;
            }

            if (this._tlCameraSDK != null && this._tlCamera != null)
            {
                if (this._tlCamera.IsArmed)
                {
                    this._tlCamera.Disarm();
                }

                this._tlCamera.Dispose();
                this._tlCamera = null;

                if (this._colorProcessor != null)
                {
                    this._colorProcessor.Dispose();
                    this._colorProcessor = null;
                }

                if (this._colorProcessorSDK != null)
                {
                    this._colorProcessorSDK.Dispose();
                    this._colorProcessorSDK = null;
                }

                this._tlCameraSDK.Dispose();
                this._tlCameraSDK = null;
            }
        }

        private void DispatcherTimerUpdateUI_Tick(object sender, EventArgs e)
        {
            if (this._tlCamera != null)
            {
                // Check if a frame is available
                if (this._tlCamera.NumberOfQueuedFrames > 0)
                {
                    var frame = this._tlCamera.GetPendingFrameOrNull();
                    if (frame != null)
                    {
                        if (this._latestDisplayBitmap != null)
                        {
                            this._latestDisplayBitmap.Dispose();
                            this._latestDisplayBitmap = null;
                        }

                        if (this._isColor)
                        {
                            var rawData = ((IImageDataUShort1D)frame.ImageData).ImageData_monoOrBGR;
                            var size = frame.ImageData.Width_pixels * frame.ImageData.Height_pixels * 3;
                            if ((this._demosaickedData == null) || (size != this._demosaickedData.Length))
                            {
                                this._demosaickedData = new ushort[frame.ImageData.Width_pixels * frame.ImageData.Height_pixels * 3];
                            }
                            this._demosaicker.Demosaic(frame.ImageData.Width_pixels, frame.ImageData.Height_pixels, 0, 0, this._colorFilterArrayPhase, ColorFormat.BGRPixel, ColorSensorType.Bayer, frame.ImageData.BitDepth, rawData, this._demosaickedData);

                            if ((this._processedImage == null) || (size != this._demosaickedData.Length))
                            {
                                this._processedImage = new ushort[frame.ImageData.Width_pixels * frame.ImageData.Height_pixels * 3];
                            }

                            ushort maxValue = (ushort)((1 << frame.ImageData.BitDepth) - 1);
                            this._colorProcessor.Transform48To48(_demosaickedData, ColorFormat.BGRPixel, 0, maxValue, 0, maxValue, 0, maxValue, 0, 0, 0, this._processedImage, ColorFormat.BGRPixel);
                            var imageData = new ImageDataUShort1D(_processedImage, frame.ImageData.Width_pixels, frame.ImageData.Height_pixels, frame.ImageData.BitDepth, ImageDataFormat.BGRPixel);
                            this._latestDisplayBitmap = imageData.ToBitmap_Format24bppRgb();
                            this.pictureBoxLiveImage.Invalidate();
                        }
                        else
                        {
                            this._latestDisplayBitmap = ((ImageDataUShort1D)(frame.ImageData)).ToBitmap_Format24bppRgb();
                            this.pictureBoxLiveImage.Invalidate();
                        }
                    }
                }
            }
        }

        private void pictureBoxLiveImage_Paint(object sender, PaintEventArgs e)
        {
            if (this._latestDisplayBitmap != null)
            {
                var scale = Math.Min((float)this.pictureBoxLiveImage.Width / this._latestDisplayBitmap.Width, (float)this.pictureBoxLiveImage.Height / this._latestDisplayBitmap.Height);
                e.Graphics.DrawImage(this._latestDisplayBitmap, new RectangleF(0, 0, this._latestDisplayBitmap.Width * scale, this._latestDisplayBitmap.Height * scale));
            }
        }
    }
}
