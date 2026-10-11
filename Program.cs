using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Windows.Forms;

namespace Steganography {
    static class Codec {
        const int Header = 44;
        static readonly byte[] Magic = Encoding.ASCII.GetBytes("STEGTR01");
        public static long Capacity(Bitmap b) { return Math.Max(0, (long)b.Width * b.Height * 3 / 8 - Header); }
        public static byte[] Pack(string name, byte[] data) {
            byte[] n = Encoding.UTF8.GetBytes(name);
            using (var m = new MemoryStream()) using (var w = new BinaryWriter(m)) {
                w.Write(n.Length); w.Write(n); w.Write(data); return m.ToArray();
            }
        }
        public static byte[] Unpack(byte[] payload, out string name) {
            if (payload.Length < 4) throw new InvalidDataException("Invalid data.");
            int n = BitConverter.ToInt32(payload, 0);
            if (n < 0 || n > payload.Length - 4) throw new InvalidDataException("Invalid file name.");
            name = Encoding.UTF8.GetString(payload, 4, n);
            byte[] data = new byte[payload.Length - 4 - n];
            Buffer.BlockCopy(payload, 4 + n, data, 0, data.Length); return data;
        }
        public static Bitmap Embed(Bitmap source, byte[] payload) {
            if (payload.LongLength > Capacity(source)) throw new InvalidOperationException("Image capacity is too small. Choose a larger image.");
            byte[] all = new byte[Header + payload.Length];
            Buffer.BlockCopy(Magic, 0, all, 0, 8);
            Buffer.BlockCopy(BitConverter.GetBytes(payload.Length), 0, all, 8, 4);
            using (var sha = SHA256.Create()) Buffer.BlockCopy(sha.ComputeHash(payload), 0, all, 12, 32);
            Buffer.BlockCopy(payload, 0, all, Header, payload.Length);
            var result = new Bitmap(source.Width, source.Height, PixelFormat.Format32bppArgb);
            long bit = 0, count = (long)all.Length * 8;
            for (int y = 0; y < source.Height; y++) for (int x = 0; x < source.Width; x++) {
                Color c = source.GetPixel(x, y); int[] rgb = { c.R, c.G, c.B };
                for (int k = 0; k < 3 && bit < count; k++, bit++) rgb[k] = (rgb[k] & 254) | ((all[(int)(bit / 8)] >> (int)(bit % 8)) & 1);
                result.SetPixel(x, y, Color.FromArgb(c.A, rgb[0], rgb[1], rgb[2]));
            }
            return result;
        }
        static byte[] Read(Bitmap b, int length) {
            byte[] bytes = new byte[length]; long bit = 0, count = (long)length * 8;
            for (int y = 0; y < b.Height && bit < count; y++) for (int x = 0; x < b.Width && bit < count; x++) {
                Color c = b.GetPixel(x, y); int[] rgb = { c.R, c.G, c.B };
                for (int k = 0; k < 3 && bit < count; k++, bit++) bytes[(int)(bit / 8)] |= (byte)((rgb[k] & 1) << (int)(bit % 8));
            }
            return bytes;
        }
        public static byte[] Extract(Bitmap b) {
            if ((long)b.Width * b.Height * 3 < Header * 8) throw new InvalidDataException("No valid hidden data was found in this image.");
            byte[] h = Read(b, Header);
            for (int i = 0; i < 8; i++) if (h[i] != Magic[i]) throw new InvalidDataException("No data hidden by this app was found.");
            int length = BitConverter.ToInt32(h, 8);
            if (length < 0 || length > Capacity(b) || length > int.MaxValue - Header) throw new InvalidDataException("The data header is corrupted.");
            byte[] all = Read(b, Header + length), payload = new byte[length];
            Buffer.BlockCopy(all, Header, payload, 0, length);
            using (var sha = SHA256.Create()) {
                byte[] hash = sha.ComputeHash(payload);
                for (int i = 0; i < 32; i++) if (hash[i] != h[12 + i]) throw new InvalidDataException("Hidden data is corrupted. Use the original PNG file.");
            }
            return payload;
        }
    }
    sealed class MainWindow : Form {
        readonly TextBox text = new TextBox { Multiline = true, ScrollBars = ScrollBars.Vertical, Dock = DockStyle.Fill, Font = new Font("Segoe UI", 11) };
        readonly Label status = new Label { AutoSize = true, Text = "Choose a carrier image." };
        Bitmap carrier;
        public MainWindow() {
            Text = "Steganography — Hide data in an image"; Width = 820; Height = 540; MinimumSize = new Size(650, 400); StartPosition = FormStartPosition.CenterScreen;
            Font = new Font("Segoe UI", 10);
            var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(16), RowCount = 5, ColumnCount = 1 };
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize)); layout.RowStyles.Add(new RowStyle(SizeType.AutoSize)); layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100)); layout.RowStyles.Add(new RowStyle(SizeType.AutoSize)); layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            var buttons = new FlowLayoutPanel { AutoSize = true, Dock = DockStyle.Fill };
            AddButton(buttons, "Choose image", SelectImage); AddButton(buttons, "Hide text", HideText); AddButton(buttons, "Hide file", HideFile); AddButton(buttons, "Extract hidden data", Extract);
            layout.Controls.Add(buttons, 0, 0); layout.Controls.Add(new Label { Text = "Text to hide or extracted text:", AutoSize = true, Margin = new Padding(3, 12, 3, 8) }, 0, 1);
            layout.Controls.Add(text, 0, 2); layout.Controls.Add(status, 0, 3);
            layout.Controls.Add(new Label { AutoSize = true, MaximumSize = new Size(740, 0), Text = "LSB method • Output is PNG. Resizing or converting to JPEG can destroy the data. Hiding is not encryption; encrypt sensitive files first.", Margin = new Padding(3, 12, 3, 3) }, 0, 4);
            Controls.Add(layout);
        }
        void AddButton(FlowLayoutPanel panel, string title, Action action) {
            var b = new Button { Text = title, AutoSize = true, Padding = new Padding(8, 5, 8, 5) };
            b.Click += delegate { try { action(); } catch (Exception ex) { MessageBox.Show(this, ex.Message, "Operation failed", MessageBoxButtons.OK, MessageBoxIcon.Warning); } }; panel.Controls.Add(b);
        }
        void SelectImage() {
            using (var d = new OpenFileDialog { Filter = "Images|*.png;*.bmp;*.jpg;*.jpeg|All files|*.*" }) {
                if (d.ShowDialog(this) != DialogResult.OK) return;
                Bitmap next; using (var loaded = new Bitmap(d.FileName)) next = new Bitmap(loaded);
                if (carrier != null) carrier.Dispose(); carrier = next;
                status.Text = String.Format("{0} × {1} pixels | Data capacity: {2:N0} bytes (including file name)", carrier.Width, carrier.Height, Codec.Capacity(carrier) - 4);
            }
        }
        void SaveHidden(string name, byte[] data) {
            if (carrier == null) throw new InvalidOperationException("Choose an image first.");
            byte[] payload = Codec.Pack(name, data);
            if (payload.LongLength > Codec.Capacity(carrier)) throw new InvalidOperationException("Image capacity is too small. Choose a larger image.");
            using (var d = new SaveFileDialog { Filter = "PNG image|*.png", DefaultExt = "png", AddExtension = true, FileName = "hidden-image.png" }) {
                if (d.ShowDialog(this) != DialogResult.OK) return;
                using (var result = Codec.Embed(carrier, payload)) result.Save(d.FileName, ImageFormat.Png);
                status.Text = "Data hidden: " + d.FileName;
            }
        }
        void HideText() { if (text.Text.Length == 0) throw new InvalidOperationException("Enter the text to hide."); SaveHidden("", Encoding.UTF8.GetBytes(text.Text)); }
        void HideFile() {
            if (carrier == null) throw new InvalidOperationException("Choose an image first.");
            using (var d = new OpenFileDialog { Filter = "All files|*.*" }) {
                if (d.ShowDialog(this) != DialogResult.OK) return;
                if (new FileInfo(d.FileName).Length > Codec.Capacity(carrier)) throw new InvalidOperationException("The file exceeds the image capacity.");
                SaveHidden(Path.GetFileName(d.FileName), File.ReadAllBytes(d.FileName));
            }
        }
        void Extract() {
            using (var d = new OpenFileDialog { Filter = "PNG / BMP|*.png;*.bmp|All files|*.*" }) {
                if (d.ShowDialog(this) != DialogResult.OK) return;
                string name; byte[] data; using (var b = new Bitmap(d.FileName)) data = Codec.Unpack(Codec.Extract(b), out name);
                if (name.Length == 0) { text.Text = Encoding.UTF8.GetString(data); status.Text = "Hidden text extracted."; }
                else using (var save = new SaveFileDialog { FileName = Path.GetFileName(name), Filter = "All files|*.*" }) {
                    if (save.ShowDialog(this) != DialogResult.OK) return;
                    File.WriteAllBytes(save.FileName, data); status.Text = "File extracted: " + save.FileName;
                }
            }
        }
        protected override void Dispose(bool disposing) { if (disposing && carrier != null) carrier.Dispose(); base.Dispose(disposing); }
    }
    static class Program {
        [STAThread] static int Main(string[] args) {
            if (args.Length > 0 && args[0] == "--self-test") { try { SelfTest(); Console.WriteLine("PASS: PNG text/file round trip, capacity, corruption, and invalid image."); return 0; } catch (Exception e) { Console.Error.WriteLine(e); return 1; } }
            Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false); Application.Run(new MainWindow()); return 0;
        }
        static void Require(bool ok) { if (!ok) throw new Exception("Test failed."); }
        static void SelfTest() {
            using (var source = new Bitmap(80, 80)) {
                using (var g = Graphics.FromImage(source)) g.Clear(Color.CornflowerBlue);
                foreach (string name in new [] { "", "sample.bin" }) {
                    byte[] original = Encoding.UTF8.GetBytes("Hello world!\nHidden data.");
                    using (var encoded = Codec.Embed(source, Codec.Pack(name, original))) using (var stream = new MemoryStream()) {
                        encoded.Save(stream, ImageFormat.Png); stream.Position = 0;
                        using (var reloaded = new Bitmap(stream)) {
                            string actual; byte[] data = Codec.Unpack(Codec.Extract(reloaded), out actual);
                            Require(actual == name && Convert.ToBase64String(data) == Convert.ToBase64String(original));
                            Color c = reloaded.GetPixel(40, 1); reloaded.SetPixel(40, 1, Color.FromArgb(c.A, c.R ^ 1, c.G, c.B));
                            bool rejected = false; try { Codec.Extract(reloaded); } catch (InvalidDataException) { rejected = true; } Require(rejected);
                        }
                    }
                }
                bool overflow = false; try { Codec.Embed(source, new byte[(int)Codec.Capacity(source) + 1]); } catch (InvalidOperationException) { overflow = true; } Require(overflow);
                bool invalid = false; try { Codec.Extract(source); } catch (InvalidDataException) { invalid = true; } Require(invalid);
                byte[] maximum = new byte[(int)Codec.Capacity(source)]; using (var full = Codec.Embed(source, maximum)) Require(Codec.Extract(full).Length == maximum.Length);
            }
        }
    }
}
