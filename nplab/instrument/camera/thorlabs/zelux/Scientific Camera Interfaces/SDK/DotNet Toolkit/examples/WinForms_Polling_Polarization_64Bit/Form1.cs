using System;
using System.ComponentModel;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using System.Windows.Threading;
using Thorlabs.TSI.CoreInterfaces;
using Thorlabs.TSI.ImageData;
using Thorlabs.TSI.ImageDataInterfaces;
using Thorlabs.TSI.PolarizationInterfaces;
using Thorlabs.TSI.PolarizationProcessor;
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

        private ushort[] _processedImage = null;
        private PolarPhase _polarPhase;
        private PolarizationProcessor _polarizationProcessor = null;
        private bool _isPolarized = false;
        private PolarizationProcessorSDK _polarizationProcessorSDK = null;

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

                this._isPolarized = this._tlCamera.CameraSensorType == CameraSensorType.MonochromePolarized;
                if (this._isPolarized)
                {
                    this._polarizationProcessorSDK = new PolarizationProcessorSDK();
                    this._polarPhase = this._tlCamera.PolarPhase;
                    this._polarizationProcessor = (PolarizationProcessor) this._polarizationProcessorSDK.CreatePolarizationProcessor();
                }

                if (!this._isPolarized)
                {
                    MessageBox.Show("No Thorlabs polarized camera detected!");
                    return;
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

                if (this._polarizationProcessor != null)
                {
                    this._polarizationProcessor.Dispose();
                    this._polarizationProcessor = null;
                }

                if (this._polarizationProcessorSDK != null)
                {
                    this._polarizationProcessorSDK.Dispose();
                    this._polarizationProcessorSDK = null;
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

                        if (this._isPolarized && !this.cbPolarImageType.Items[this.cbPolarImageType.SelectedIndex].ToString().Equals("Unprocessed"))
                        {
                            var rawData = ((IImageDataUShort1D)frame.ImageData).ImageData_monoOrBGR;
                            var size = frame.ImageData.Width_pixels * frame.ImageData.Height_pixels;

                            if ((this._processedImage == null))
                            {
                                this._processedImage = new ushort[size];
                            }

                            ushort maxValue = (ushort)((1 << frame.ImageData.BitDepth) - 1);
                            var selectedPolarizedImageType = this.cbPolarImageType.Items[this.cbPolarImageType.SelectedIndex].ToString();

                            if (selectedPolarizedImageType.Equals("Intensity"))
                            {
                                this._polarizationProcessor.TransformToIntensity(this._polarPhase, rawData, 0, 0, frame.ImageData.Width_pixels, frame.ImageData.Height_pixels, frame.ImageData.BitDepth, maxValue, _processedImage);
                            }

                            switch (selectedPolarizedImageType)
                            {
                                case "Intensity":
                                {
                                    this._polarizationProcessor.TransformToIntensity(this._polarPhase, rawData, 0, 0, frame.ImageData.Width_pixels, frame.ImageData.Height_pixels, frame.ImageData.BitDepth, maxValue, _processedImage);
                                }
                                    break;
                                case "Azimuth":
                                {
                                    this._polarizationProcessor.TransformToAzimuth(this._polarPhase, rawData, 0, 0, frame.ImageData.Width_pixels, frame.ImageData.Height_pixels, frame.ImageData.BitDepth, maxValue, _processedImage);
                                }
                                    break;
                                case "DoLP":
                                {
                                    this._polarizationProcessor.TransformToDoLP(this._polarPhase, rawData, 0, 0, frame.ImageData.Width_pixels, frame.ImageData.Height_pixels, frame.ImageData.BitDepth, maxValue, _processedImage);
                                }
                                    break;
                            }

                            var imageData = new ImageDataUShort1D(_processedImage, frame.ImageData.Width_pixels, frame.ImageData.Height_pixels, frame.ImageData.BitDepth, ImageDataFormat.Monochrome);
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

        private void cbPolarImageType_SelectedIndexChanged(object sender, EventArgs e)
        {

        }
    }
}
