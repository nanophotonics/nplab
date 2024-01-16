namespace Example_DotNet_Camera_Interface
{
    partial class Form1
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (this.components != null))
            {
                this.components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.pictureBoxLiveImage = new System.Windows.Forms.PictureBox();
            this.gbPolarImageType = new System.Windows.Forms.GroupBox();
            this.cbPolarImageType = new System.Windows.Forms.ComboBox();
            ((System.ComponentModel.ISupportInitialize)(this.pictureBoxLiveImage)).BeginInit();
            this.gbPolarImageType.SuspendLayout();
            this.SuspendLayout();
            // 
            // pictureBoxLiveImage
            // 
            this.pictureBoxLiveImage.Anchor = ((System.Windows.Forms.AnchorStyles)((((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom)
            | System.Windows.Forms.AnchorStyles.Left)
            | System.Windows.Forms.AnchorStyles.Right)));
            this.pictureBoxLiveImage.Location = new System.Drawing.Point(12, 66);
            this.pictureBoxLiveImage.Name = "pictureBoxLiveImage";
            this.pictureBoxLiveImage.Size = new System.Drawing.Size(497, 425);
            this.pictureBoxLiveImage.TabIndex = 0;
            this.pictureBoxLiveImage.TabStop = false;
            this.pictureBoxLiveImage.Paint += new System.Windows.Forms.PaintEventHandler(this.pictureBoxLiveImage_Paint);
            // 
            // gbPolarImageType
            // 
            this.gbPolarImageType.Controls.Add(this.cbPolarImageType);
            this.gbPolarImageType.Location = new System.Drawing.Point(12, 12);
            this.gbPolarImageType.Name = "gbPolarImageType";
            this.gbPolarImageType.Size = new System.Drawing.Size(146, 48);
            this.gbPolarImageType.TabIndex = 35;
            this.gbPolarImageType.TabStop = false;
            this.gbPolarImageType.Text = "Polarization Image Type";
            // 
            // cbPolarImageType
            // 
            this.cbPolarImageType.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.cbPolarImageType.FormattingEnabled = true;
            this.cbPolarImageType.Location = new System.Drawing.Point(13, 17);
            this.cbPolarImageType.Name = "cbPolarImageType";
            this.cbPolarImageType.Size = new System.Drawing.Size(121, 21);
            this.cbPolarImageType.TabIndex = 21;
            this.cbPolarImageType.SelectedIndexChanged += new System.EventHandler(this.cbPolarImageType_SelectedIndexChanged);
            this.cbPolarImageType.Items.Add("Intensity");
            this.cbPolarImageType.Items.Add("DoLP");
            this.cbPolarImageType.Items.Add("Azimuth");
            this.cbPolarImageType.Items.Add("Unprocessed");
            this.cbPolarImageType.SelectedIndex = 0;
            // 
            // Form1
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(518, 500);
            this.Controls.Add(this.gbPolarImageType);
            this.Controls.Add(this.pictureBoxLiveImage);
            this.Name = "Form1";
            this.Text = "TLCamera Example";
            ((System.ComponentModel.ISupportInitialize)(this.pictureBoxLiveImage)).EndInit();
            this.gbPolarImageType.ResumeLayout(false);
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.PictureBox pictureBoxLiveImage;
        private System.Windows.Forms.GroupBox gbPolarImageType;
        private System.Windows.Forms.ComboBox cbPolarImageType;
    }
}

