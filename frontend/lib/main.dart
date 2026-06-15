import 'dart:io';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:open_file/open_file.dart';
import 'package:path_provider/path_provider.dart';

import 'services/api_service.dart';

void main() {
  runApp(const EcuAiApp());
}

class EcuAiApp extends StatelessWidget {
  const EcuAiApp({super.key});

  @override
  Widget build(BuildContext context) {
    const seed = Color(0xFF2563EB);

    return MaterialApp(
      title: 'ECU AI App',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: seed,
          brightness: Brightness.light,
        ),
        scaffoldBackgroundColor: const Color(0xFFF5F7FB),
        useMaterial3: true,
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Color(0xFFD9E0EC)),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Color(0xFFD9E0EC)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: seed, width: 1.5),
          ),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 14,
          ),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            minimumSize: const Size(0, 46),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            side: const BorderSide(color: Color(0xFFC9D4E5)),
          ),
        ),
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  static const double _mobileBreakpoint = 720;

  final api = ApiService();

  final rpmController = TextEditingController();
  final boostController = TextEditingController();
  final injectionController = TextEditingController();
  final afrController = TextEditingController();
  final displacementController = TextEditingController();
  final stockHpController = TextEditingController();
  final mapTextController = TextEditingController();

  String fuelType = 'diesel';
  String inputMode = 'file';
  String calibrationMapType = 'soi';
  bool isTurbo = true;

  bool loadingParse = false;
  bool loadingCalibrationAnalyze = false;
  bool loadingAnalyze = false;
  bool loadingFuelMap = false;
  bool loadingHeatmap = false;
  bool loadingReport = false;

  String? errorMessage;

  double? stage1GainPercent;
  String? potentialClass;
  double? estimatedHpAfterStage1;

  Map<String, dynamic>? fuelMapResult;
  Map<String, dynamic>? calibrationResult;
  Map<String, dynamic>? derivedFeatures;
  Map<String, dynamic>? parsedCalibrationMap;
  String? calibrationError;
  String? originalCalibrationFileName;
  Uint8List? originalCalibrationBytes;
  String? modifiedCalibrationFileName;
  Uint8List? modifiedCalibrationBytes;
  String? definitionsCalibrationFileName;
  Uint8List? definitionsCalibrationBytes;
  String? selectedMapFileName;
  String? selectedBinaryEcuFileName;
  Uint8List? selectedBinaryEcuBytes;
  Uint8List? heatmapBytes;
  String? savedPdfPath;
  int mobileTabIndex = 0;

  static const String sampleSoiMap = '''
        0.0     5.0     10.0    15.0    20.0    25.0    30.0    35.0    40.0    45.0    50.0    55.0
100     -10.99  -10.99  -10.99  -10.99  -10.99  -10.99  -10.99  -10.99  -10.99  -10.99  -10.99  -10.99
400     -0.00   -0.00   -0.00   -1.99   -5.49   -9.00   -12.00  -13.99  -15.00  -15.00  -15.00  -15.00
800     -0.00   -0.00   -0.00   -1.99   -5.49   -9.00   -12.00  -13.99  -15.00  -15.00  -15.00  -15.00
1250    -0.70   -0.70   -0.70   -1.99   -5.49   -9.00   -12.00  -13.48  -15.00  -15.00  -15.00  -15.00
1500    -1.71   -1.71   -1.71   -2.39   -4.64   -6.14   -7.60   -10.01  -12.31  -13.01  -13.01  -13.01
1750    -2.42   -2.42   -2.42   -3.21   -4.85   -6.17   -7.29   -8.51   -10.67  -11.51  -11.51  -11.51
2000    -2.95   -2.95   -2.95   -3.68   -5.04   -6.24   -7.29   -8.51   -10.50  -12.00  -12.00  -12.00
2250    -3.75   -3.75   -3.75   -4.43   -5.88   -7.03   -7.99   -9.10   -11.04  -13.24  -13.24  -13.24
2500    -5.51   -5.51   -5.51   -6.21   -7.15   -8.16   -9.31   -10.60  -12.00  -14.60  -14.60  -14.60
3000    -9.33   -9.33   -9.33   -10.95  -12.28  -13.24  -14.20  -15.77  -16.57  -17.72  -18.42  -18.42
3500    -12.26  -12.26  -12.26  -14.44  -16.55  -17.39  -18.07  -19.01  -19.88  -21.19  -22.24  -22.24
4000    -15.00  -15.00  -15.00  -17.25  -19.99  -21.00  -21.59  -22.01  -22.50  -23.51  -24.00  -24.00
4250    -15.94  -15.94  -15.94  -17.95  -20.81  -21.47  -21.99  -22.43  -23.02  -23.98  -24.45  -24.45
5000    -17.35  -17.35  -17.35  -19.17  -21.75  -22.52  -22.99  -23.42  -24.09  -25.03  -25.50  -25.50
''';

  double? parseNumber(String value) {
    final normalized = value.trim().replaceAll(',', '.');
    if (normalized.isEmpty) return null;
    return double.tryParse(normalized);
  }

  Map<String, dynamic>? asStringMap(dynamic value) {
    if (value is Map) {
      return Map<String, dynamic>.from(value);
    }
    return null;
  }

  Map<String, dynamic> buildInputData() {
    final input = <String, dynamic>{
      'engine_displacement': parseNumber(displacementController.text),
      'fuel_type': fuelType,
      'is_turbo': isTurbo,
      'stock_hp': stockHpController.text.trim().isEmpty
          ? null
          : parseNumber(stockHpController.text),
    };

    if (inputMode == 'file' && parsedCalibrationMap != null) {
      input['calibration_map'] = parsedCalibrationMap;
    } else if (inputMode == 'paste' &&
        mapTextController.text.trim().isNotEmpty) {
      input['calibration_map_text'] = mapTextController.text.trim();
      input['calibration_map_type'] = calibrationMapType;
    } else {
      input['rpm'] = parseNumber(rpmController.text);
      input['boost_pressure'] = parseNumber(boostController.text);
      input['injection_quantity'] = parseNumber(injectionController.text);
      input['afr'] = parseNumber(afrController.text);
    }

    return input;
  }

  Future<({String name, Uint8List bytes})?> pickCalibrationFile([
    List<String>? extensions,
  ]) async {
    final picked = await FilePicker.platform.pickFiles(
      type: extensions == null ? FileType.any : FileType.custom,
      allowedExtensions: extensions,
      withData: true,
    );

    if (picked == null || picked.files.isEmpty) {
      return null;
    }

    final file = picked.files.single;
    final path = file.path;
    final bytes =
        file.bytes ?? (path == null ? null : await File(path).readAsBytes());
    if (bytes == null) {
      throw Exception('Nu am putut citi fisierul selectat.');
    }
    return (name: file.name, bytes: bytes);
  }

  Future<void> selectCalibrationOriginal() async {
    try {
      final file = await pickCalibrationFile();
      if (file == null) return;
      setState(() {
        originalCalibrationFileName = file.name;
        originalCalibrationBytes = file.bytes;
        calibrationResult = null;
        calibrationError = null;
      });
    } catch (e) {
      setState(() {
        calibrationError = 'Eroare la fisierul original: $e';
      });
    }
  }

  Future<void> selectCalibrationModified() async {
    try {
      final file = await pickCalibrationFile();
      if (file == null) return;
      setState(() {
        modifiedCalibrationFileName = file.name;
        modifiedCalibrationBytes = file.bytes;
        calibrationResult = null;
        calibrationError = null;
      });
    } catch (e) {
      setState(() {
        calibrationError = 'Eroare la fisierul modificat: $e';
      });
    }
  }

  Future<void> selectCalibrationDefinitions() async {
    try {
      final file = await pickCalibrationFile(['csv', 'json']);
      if (file == null) return;
      setState(() {
        definitionsCalibrationFileName = file.name;
        definitionsCalibrationBytes = file.bytes;
        calibrationResult = null;
        calibrationError = null;
      });
    } catch (e) {
      setState(() {
        calibrationError = 'Eroare la definitii: $e';
      });
    }
  }

  Future<void> analyzeCalibrationFiles() async {
    FocusScope.of(context).unfocus();

    final originalName = originalCalibrationFileName;
    final originalBytes = originalCalibrationBytes;
    if (originalName == null || originalBytes == null) {
      setState(() {
        calibrationError = 'Incarca fisierul original inainte de analiza.';
      });
      return;
    }

    setState(() {
      loadingCalibrationAnalyze = true;
      calibrationError = null;
    });

    try {
      final result = await api.analyzeCalibration(
        originalFileName: originalName,
        originalBytes: originalBytes,
        modifiedFileName: modifiedCalibrationFileName,
        modifiedBytes: modifiedCalibrationBytes,
        definitionsFileName: definitionsCalibrationFileName,
        definitionsBytes: definitionsCalibrationBytes,
        engineDisplacement: parseNumber(displacementController.text),
        fuelType: fuelType,
        isTurbo: isTurbo,
        stockHp: parseNumber(stockHpController.text),
      );

      setState(() {
        calibrationResult = result;
      });
    } catch (e) {
      setState(() {
        calibrationError = 'Eroare la analiza calibrarii: $e';
      });
    } finally {
      setState(() {
        loadingCalibrationAnalyze = false;
      });
    }
  }

  Future<void> importMapFile() async {
    FocusScope.of(context).unfocus();

    setState(() {
      loadingParse = true;
      errorMessage = null;
    });

    try {
      final picked = await FilePicker.platform.pickFiles(
        type: FileType.any,
        withData: true,
      );

      if (picked == null || picked.files.isEmpty) {
        return;
      }

      final file = picked.files.single;
      final path = file.path;
      final bytes =
          file.bytes ?? (path == null ? null : await File(path).readAsBytes());
      if (bytes == null) {
        throw Exception('Nu am putut citi fisierul selectat.');
      }

      try {
        final result = await api.parseMapFile(
          fileName: file.name,
          bytes: bytes,
          mapType: calibrationMapType,
          fuelType: fuelType,
          isTurbo: isTurbo,
        );

        setState(() {
          selectedMapFileName = result['file_name']?.toString() ?? file.name;
          selectedBinaryEcuFileName = null;
          selectedBinaryEcuBytes = null;
          parsedCalibrationMap = asStringMap(result['calibration_map']);
          derivedFeatures = asStringMap(result['derived_features']);
          stage1GainPercent = null;
          potentialClass = null;
          estimatedHpAfterStage1 = null;
          fuelMapResult = null;
          heatmapBytes = null;
          savedPdfPath = null;
        });

        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Harta importata: ${file.name}')),
        );
        return;
      } catch (_) {
        setState(() {
          selectedMapFileName = file.name;
          selectedBinaryEcuFileName = file.name;
          selectedBinaryEcuBytes = bytes;
          parsedCalibrationMap = null;
          derivedFeatures = null;
          stage1GainPercent = null;
          potentialClass = null;
          estimatedHpAfterStage1 = null;
          fuelMapResult = null;
          heatmapBytes = null;
          savedPdfPath = null;
        });
      }

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Fisier ECU binar importat: ${file.name}')),
      );
    } catch (e) {
      setState(() {
        errorMessage = 'Eroare la importul hartii: $e';
      });
    } finally {
      setState(() {
        loadingParse = false;
      });
    }
  }

  Future<void> analyzeData() async {
    FocusScope.of(context).unfocus();
    final showResultsAfterAnalyze =
        MediaQuery.sizeOf(context).width < _mobileBreakpoint;

    setState(() {
      loadingAnalyze = true;
      errorMessage = null;
    });

    try {
      if (inputMode == 'file' && selectedBinaryEcuBytes != null) {
        final calibration = await api.analyzeCalibration(
          originalFileName: selectedBinaryEcuFileName ?? selectedMapFileName!,
          originalBytes: selectedBinaryEcuBytes!,
          definitionsFileName: definitionsCalibrationFileName,
          definitionsBytes: definitionsCalibrationBytes,
          engineDisplacement: parseNumber(displacementController.text),
          fuelType: fuelType,
          isTurbo: isTurbo,
          stockHp: parseNumber(stockHpController.text),
        );
        final estimate = asStringMap(calibration['power_estimate']);

        if (estimate == null || estimate['available'] != true) {
          throw Exception(
            estimate?['reason'] ??
                'Fisierul binar are nevoie de definitions CSV/JSON pentru estimare.',
          );
        }

        setState(() {
          calibrationResult = calibration;
          stage1GainPercent = (estimate['stage1_gain_percent'] as num?)
              ?.toDouble();
          potentialClass = estimate['potential_class']?.toString();
          estimatedHpAfterStage1 =
              (estimate['estimated_hp_after_stage1'] as num?)?.toDouble();
          derivedFeatures = asStringMap(estimate['derived_inputs']);
          if (showResultsAfterAnalyze) {
            mobileTabIndex = 1;
          }
        });
        return;
      }

      final result = await api.analyze(buildInputData());

      setState(() {
        stage1GainPercent = (result['stage1_gain_percent'] as num?)?.toDouble();
        potentialClass = result['potential_class']?.toString();
        estimatedHpAfterStage1 = (result['estimated_hp_after_stage1'] as num?)
            ?.toDouble();
        derivedFeatures = asStringMap(result['derived_features']);
        if (showResultsAfterAnalyze) {
          mobileTabIndex = 1;
        }
      });
    } catch (e) {
      setState(() {
        errorMessage = 'Eroare la analiza: $e';
      });
    } finally {
      setState(() {
        loadingAnalyze = false;
      });
    }
  }

  Future<void> generateFuelMap() async {
    FocusScope.of(context).unfocus();
    final showOutputAfterGenerate =
        MediaQuery.sizeOf(context).width < _mobileBreakpoint;

    setState(() {
      loadingFuelMap = true;
      errorMessage = null;
    });

    try {
      final result = await api.fuelMap(buildInputData());

      setState(() {
        fuelMapResult = result;
        stage1GainPercent ??= (result['stage1_gain_percent'] as num?)
            ?.toDouble();
        potentialClass ??= result['potential_class']?.toString();
        derivedFeatures = asStringMap(result['derived_features']);
        if (showOutputAfterGenerate) {
          mobileTabIndex = 2;
        }
      });

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Fuel map generat cu succes.')),
      );
    } catch (e) {
      setState(() {
        errorMessage = 'Eroare la generarea fuel map: $e';
      });
    } finally {
      setState(() {
        loadingFuelMap = false;
      });
    }
  }

  Future<void> viewHeatmap() async {
    FocusScope.of(context).unfocus();

    setState(() {
      loadingHeatmap = true;
      errorMessage = null;
    });

    try {
      final bytes = await api.fuelMapImage(buildInputData());

      setState(() {
        heatmapBytes = bytes;
      });

      if (!mounted) return;
      showDialog(
        context: context,
        builder: (context) => Dialog(
          insetPadding: const EdgeInsets.all(24),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 920, maxHeight: 720),
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                children: [
                  Row(
                    children: [
                      const Icon(Icons.grid_on_rounded),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'Fuel Map Heatmap',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                      ),
                      IconButton(
                        tooltip: 'Inchide',
                        onPressed: () => Navigator.of(context).pop(),
                        icon: const Icon(Icons.close),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Expanded(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: InteractiveViewer(
                        child: Image.memory(bytes, fit: BoxFit.contain),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    } catch (e) {
      setState(() {
        errorMessage = 'Eroare la generarea heatmap-ului: $e';
      });
    } finally {
      setState(() {
        loadingHeatmap = false;
      });
    }
  }

  Future<void> generatePdfReport() async {
    FocusScope.of(context).unfocus();

    setState(() {
      loadingReport = true;
      errorMessage = null;
    });

    try {
      final bytes = await api.report(buildInputData());

      final directory = await getApplicationDocumentsDirectory();
      final file = File(
        '${directory.path}${Platform.pathSeparator}stage1_report.pdf',
      );
      await file.writeAsBytes(bytes, flush: true);

      setState(() {
        savedPdfPath = file.path;
      });

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('PDF salvat in: ${file.path}'),
          action: SnackBarAction(
            label: 'Open',
            onPressed: () {
              OpenFile.open(file.path);
            },
          ),
        ),
      );
    } catch (e) {
      setState(() {
        errorMessage = 'Eroare la generarea PDF-ului: $e';
      });
    } finally {
      setState(() {
        loadingReport = false;
      });
    }
  }

  @override
  void dispose() {
    rpmController.dispose();
    boostController.dispose();
    injectionController.dispose();
    afrController.dispose();
    displacementController.dispose();
    stockHpController.dispose();
    mapTextController.dispose();
    super.dispose();
  }

  Widget buildTextField(
    String label,
    TextEditingController controller, {
    String? hint,
    String? suffix,
  }) {
    return TextField(
      controller: controller,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        suffixText: suffix,
      ),
    );
  }

  List<dynamic> asList(dynamic value) {
    return value is List ? value : const [];
  }

  String formatFileSize(int? bytes) {
    if (bytes == null) return '-';
    if (bytes >= 1024 * 1024) {
      return '${(bytes / (1024 * 1024)).toStringAsFixed(2)} MB';
    }
    if (bytes >= 1024) {
      return '${(bytes / 1024).toStringAsFixed(1)} KB';
    }
    return '$bytes B';
  }

  Widget buildCalibrationFileButton({
    required String label,
    required String? fileName,
    required IconData icon,
    required VoidCallback onPressed,
    bool optional = false,
  }) {
    final hasFile = fileName != null;
    return OutlinedButton.icon(
      onPressed: loadingCalibrationAnalyze ? null : onPressed,
      icon: Icon(hasFile ? Icons.check_circle_rounded : icon),
      label: Align(
        alignment: Alignment.centerLeft,
        child: Text(
          hasFile ? fileName : '$label${optional ? ' optional' : ''}',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ),
    );
  }

  Widget buildCalibrationAnalyzer(bool busy) {
    final summary = asStringMap(calibrationResult?['summary']);
    final binaryDiff = asStringMap(calibrationResult?['binary_diff']);
    final powerEstimate = asStringMap(calibrationResult?['power_estimate']);
    final recommendations = asList(calibrationResult?['recommendations']);
    final findings = asList(calibrationResult?['findings']);
    final warnings = asList(calibrationResult?['warnings']);
    final maps = asList(calibrationResult?['maps']);

    return _SectionPanel(
      icon: Icons.manage_search_rounded,
      title: 'Calibration Analyzer',
      subtitle:
          'Compara fisiere ECU si extrage diferente pe harti cand exista definitii.',
      accentColor: const Color(0xFF0F766E),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth >= 760;
              final width = isWide
                  ? (constraints.maxWidth - 28) / 3
                  : constraints.maxWidth;
              return Wrap(
                spacing: 14,
                runSpacing: 14,
                children: [
                  SizedBox(
                    width: width,
                    child: buildCalibrationFileButton(
                      label: 'Original file',
                      fileName: originalCalibrationFileName,
                      icon: Icons.source_rounded,
                      onPressed: selectCalibrationOriginal,
                    ),
                  ),
                  SizedBox(
                    width: width,
                    child: buildCalibrationFileButton(
                      label: 'Modified file',
                      fileName: modifiedCalibrationFileName,
                      icon: Icons.compare_arrows_rounded,
                      onPressed: selectCalibrationModified,
                      optional: true,
                    ),
                  ),
                  SizedBox(
                    width: width,
                    child: buildCalibrationFileButton(
                      label: 'Definitions CSV/JSON',
                      fileName: definitionsCalibrationFileName,
                      icon: Icons.list_alt_rounded,
                      onPressed: selectCalibrationDefinitions,
                      optional: true,
                    ),
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: busy ? null : analyzeCalibrationFiles,
                  icon: loadingCalibrationAnalyze
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2.3),
                        )
                      : const Icon(Icons.analytics_rounded),
                  label: const Text('Analyze calibration'),
                ),
              ),
              const SizedBox(width: 10),
              IconButton.outlined(
                tooltip: 'Clear calibration files',
                onPressed: busy
                    ? null
                    : () {
                        setState(() {
                          originalCalibrationFileName = null;
                          originalCalibrationBytes = null;
                          modifiedCalibrationFileName = null;
                          modifiedCalibrationBytes = null;
                          definitionsCalibrationFileName = null;
                          definitionsCalibrationBytes = null;
                          calibrationResult = null;
                          calibrationError = null;
                        });
                      },
                icon: const Icon(Icons.clear_rounded),
              ),
            ],
          ),
          if (calibrationError != null) ...[
            const SizedBox(height: 14),
            _InlineNotice(
              icon: Icons.error_outline_rounded,
              text: calibrationError!,
              color: const Color(0xFFB91C1C),
            ),
          ],
          if (summary != null) ...[
            const SizedBox(height: 14),
            LayoutBuilder(
              builder: (context, constraints) {
                final isWide = constraints.maxWidth >= 760;
                final tileWidth = isWide
                    ? (constraints.maxWidth - 28) / 3
                    : constraints.maxWidth;
                return Wrap(
                  spacing: 14,
                  runSpacing: 14,
                  children: [
                    SizedBox(
                      width: tileWidth,
                      child: _CompactMetric(
                        icon: Icons.memory_rounded,
                        label: 'Original',
                        value: formatFileSize(summary['original_size'] as int?),
                      ),
                    ),
                    SizedBox(
                      width: tileWidth,
                      child: _CompactMetric(
                        icon: Icons.table_chart_rounded,
                        label: 'Maps extracted',
                        value: '${summary['maps_extracted'] ?? 0}',
                      ),
                    ),
                    SizedBox(
                      width: tileWidth,
                      child: _CompactMetric(
                        icon: Icons.difference_rounded,
                        label: 'Maps changed',
                        value: '${summary['maps_changed'] ?? 0}',
                      ),
                    ),
                  ],
                );
              },
            ),
          ],
          if (binaryDiff != null) ...[
            const SizedBox(height: 14),
            _InlineNotice(
              icon: Icons.data_object_rounded,
              text:
                  'Binary diff: ${binaryDiff['changed_bytes']} bytes changed (${binaryDiff['changed_percent']}%).',
              color: const Color(0xFF0F766E),
            ),
          ],
          if (powerEstimate != null) ...[
            const SizedBox(height: 14),
            _PowerEstimatePanel(estimate: powerEstimate),
          ],
          if (recommendations.isNotEmpty) ...[
            const SizedBox(height: 14),
            _RecommendationPanel(items: recommendations),
          ],
          if (findings.isNotEmpty) ...[
            const SizedBox(height: 14),
            for (final item in findings.take(5)) ...[
              _FindingRow(finding: Map<String, dynamic>.from(item as Map)),
              const SizedBox(height: 8),
            ],
          ],
          if (maps.isNotEmpty) ...[
            const SizedBox(height: 6),
            _MapBrowser(items: maps),
          ],
          if (warnings.isNotEmpty) ...[
            const SizedBox(height: 14),
            for (final warning in warnings.take(4))
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: _InlineNotice(
                  icon: Icons.info_outline_rounded,
                  text: '$warning',
                  color: const Color(0xFF92400E),
                ),
              ),
          ],
        ],
      ),
    );
  }

  Widget buildInputForm(bool busy) {
    final manualFields = [
      buildTextField('RPM', rpmController, hint: '3500'),
      buildTextField(
        'Boost Pressure',
        boostController,
        hint: '1.6',
        suffix: 'bar',
      ),
      buildTextField(
        'Injection Quantity',
        injectionController,
        hint: '55',
        suffix: 'mg',
      ),
      buildTextField('AFR', afrController, hint: '14.7'),
    ];
    final engineFields = [
      buildTextField(
        'Engine Displacement',
        displacementController,
        hint: '2.0',
        suffix: 'L',
      ),
      buildTextField('Stock HP', stockHpController, hint: '150', suffix: 'hp'),
    ];

    return _SectionPanel(
      icon: Icons.tune_rounded,
      title: 'Input ECU',
      subtitle:
          'Importa o harta exportata din WinOLS si verifica valorile extrase.',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: SegmentedButton<String>(
              segments: const [
                ButtonSegment(
                  value: 'file',
                  icon: Icon(Icons.upload_file_rounded),
                  label: Text('Fisier'),
                ),
                ButtonSegment(
                  value: 'paste',
                  icon: Icon(Icons.grid_on_rounded),
                  label: Text('Paste'),
                ),
                ButtonSegment(
                  value: 'manual',
                  icon: Icon(Icons.edit_note_rounded),
                  label: Text('Manual'),
                ),
              ],
              selected: {inputMode},
              onSelectionChanged: busy
                  ? null
                  : (selection) {
                      setState(() {
                        inputMode = selection.first;
                      });
                    },
            ),
          ),
          const SizedBox(height: 16),
          if (inputMode == 'file') ...[
            LayoutBuilder(
              builder: (context, constraints) {
                final isWide = constraints.maxWidth >= 620;
                return Wrap(
                  spacing: 14,
                  runSpacing: 14,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    SizedBox(
                      width: isWide
                          ? (constraints.maxWidth - 14) / 2
                          : constraints.maxWidth,
                      child: DropdownButtonFormField<String>(
                        initialValue: calibrationMapType,
                        decoration: const InputDecoration(
                          labelText: 'Map Type',
                          prefixIcon: Icon(Icons.table_chart_rounded),
                        ),
                        items: const [
                          DropdownMenuItem(
                            value: 'soi',
                            child: Text('SOI timing'),
                          ),
                          DropdownMenuItem(
                            value: 'fuel',
                            child: Text('Fuel qty'),
                          ),
                          DropdownMenuItem(
                            value: 'boost',
                            child: Text('Boost'),
                          ),
                          DropdownMenuItem(
                            value: 'torque',
                            child: Text('Torque'),
                          ),
                        ],
                        onChanged: busy
                            ? null
                            : (value) {
                                if (value == null) return;
                                setState(() {
                                  calibrationMapType = value;
                                  parsedCalibrationMap = null;
                                  selectedMapFileName = null;
                                  selectedBinaryEcuFileName = null;
                                  selectedBinaryEcuBytes = null;
                                  derivedFeatures = null;
                                  fuelMapResult = null;
                                });
                              },
                      ),
                    ),
                    SizedBox(
                      width: isWide
                          ? (constraints.maxWidth - 14) / 2
                          : constraints.maxWidth,
                      child: Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: busy ? null : importMapFile,
                              icon: loadingParse
                                  ? const SizedBox(
                                      width: 18,
                                      height: 18,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2.2,
                                      ),
                                    )
                                  : const Icon(Icons.upload_file_rounded),
                              label: const Text('Import file'),
                            ),
                          ),
                          const SizedBox(width: 10),
                          IconButton.outlined(
                            tooltip: 'Clear file',
                            onPressed: busy
                                ? null
                                : () {
                                    setState(() {
                                      parsedCalibrationMap = null;
                                      selectedMapFileName = null;
                                      selectedBinaryEcuFileName = null;
                                      selectedBinaryEcuBytes = null;
                                      derivedFeatures = null;
                                      fuelMapResult = null;
                                    });
                                  },
                            icon: const Icon(Icons.clear_rounded),
                          ),
                        ],
                      ),
                    ),
                  ],
                );
              },
            ),
            if (selectedMapFileName != null) ...[
              const SizedBox(height: 14),
              _ImportedMapNote(
                fileName: selectedMapFileName!,
                isBinary: selectedBinaryEcuBytes != null,
              ),
            ],
            if (derivedFeatures != null) ...[
              const SizedBox(height: 14),
              _DerivedMapSummary(features: derivedFeatures!),
            ],
            const SizedBox(height: 16),
          ] else if (inputMode == 'paste') ...[
            LayoutBuilder(
              builder: (context, constraints) {
                final isWide = constraints.maxWidth >= 620;
                return Wrap(
                  spacing: 14,
                  runSpacing: 14,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    SizedBox(
                      width: isWide
                          ? (constraints.maxWidth - 14) / 2
                          : constraints.maxWidth,
                      child: DropdownButtonFormField<String>(
                        initialValue: calibrationMapType,
                        decoration: const InputDecoration(
                          labelText: 'Map Type',
                          prefixIcon: Icon(Icons.table_chart_rounded),
                        ),
                        items: const [
                          DropdownMenuItem(
                            value: 'soi',
                            child: Text('SOI timing'),
                          ),
                          DropdownMenuItem(
                            value: 'fuel',
                            child: Text('Fuel qty'),
                          ),
                          DropdownMenuItem(
                            value: 'boost',
                            child: Text('Boost'),
                          ),
                          DropdownMenuItem(
                            value: 'torque',
                            child: Text('Torque'),
                          ),
                        ],
                        onChanged: busy
                            ? null
                            : (value) {
                                if (value == null) return;
                                setState(() {
                                  calibrationMapType = value;
                                });
                              },
                      ),
                    ),
                    SizedBox(
                      width: isWide
                          ? (constraints.maxWidth - 14) / 2
                          : constraints.maxWidth,
                      child: Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: busy
                                  ? null
                                  : () {
                                      setState(() {
                                        mapTextController.text = sampleSoiMap
                                            .trim();
                                        calibrationMapType = 'soi';
                                        selectedBinaryEcuFileName = null;
                                        selectedBinaryEcuBytes = null;
                                      });
                                    },
                              icon: const Icon(Icons.dataset_rounded),
                              label: const Text('Load sample'),
                            ),
                          ),
                          const SizedBox(width: 10),
                          IconButton.outlined(
                            tooltip: 'Clear map',
                            onPressed: busy
                                ? null
                                : () {
                                    setState(() {
                                      mapTextController.clear();
                                      selectedBinaryEcuFileName = null;
                                      selectedBinaryEcuBytes = null;
                                    });
                                  },
                            icon: const Icon(Icons.clear_rounded),
                          ),
                        ],
                      ),
                    ),
                  ],
                );
              },
            ),
            const SizedBox(height: 14),
            TextField(
              controller: mapTextController,
              minLines: 10,
              maxLines: 16,
              keyboardType: TextInputType.multiline,
              style: const TextStyle(
                fontFamily: 'monospace',
                fontSize: 12.5,
                height: 1.35,
              ),
              decoration: const InputDecoration(
                labelText: 'WinOLS table paste',
                hintText:
                    'Prima linie poate fi axa X; randurile urmatoare: RPM + valorile hartii',
                alignLabelWithHint: true,
              ),
            ),
            const SizedBox(height: 16),
          ] else ...[
            LayoutBuilder(
              builder: (context, constraints) {
                final isWide = constraints.maxWidth >= 680;
                return Wrap(
                  spacing: 14,
                  runSpacing: 14,
                  children: [
                    for (final field in manualFields)
                      SizedBox(
                        width: isWide
                            ? (constraints.maxWidth - 14) / 2
                            : constraints.maxWidth,
                        child: field,
                      ),
                  ],
                );
              },
            ),
            const SizedBox(height: 16),
          ],
          LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth >= 680;
              return Wrap(
                spacing: 14,
                runSpacing: 14,
                children: [
                  for (final field in engineFields)
                    SizedBox(
                      width: isWide
                          ? (constraints.maxWidth - 14) / 2
                          : constraints.maxWidth,
                      child: field,
                    ),
                ],
              );
            },
          ),
          const SizedBox(height: 16),
          LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth >= 620;
              return Wrap(
                spacing: 14,
                runSpacing: 14,
                children: [
                  SizedBox(
                    width: isWide
                        ? (constraints.maxWidth - 14) / 2
                        : constraints.maxWidth,
                    child: DropdownButtonFormField<String>(
                      initialValue: fuelType,
                      decoration: const InputDecoration(
                        labelText: 'Fuel Type',
                        prefixIcon: Icon(Icons.local_gas_station_rounded),
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: 'diesel',
                          child: Text('Diesel'),
                        ),
                        DropdownMenuItem(
                          value: 'petrol',
                          child: Text('Petrol'),
                        ),
                      ],
                      onChanged: busy
                          ? null
                          : (value) {
                              if (value == null) return;
                              setState(() {
                                fuelType = value;
                              });
                            },
                    ),
                  ),
                  SizedBox(
                    width: isWide
                        ? (constraints.maxWidth - 14) / 2
                        : constraints.maxWidth,
                    child: Container(
                      height: 56,
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFFD9E0EC)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.speed_rounded),
                          const SizedBox(width: 12),
                          const Expanded(
                            child: Text(
                              'Turbo',
                              style: TextStyle(fontWeight: FontWeight.w600),
                            ),
                          ),
                          Switch(
                            value: isTurbo,
                            onChanged: busy
                                ? null
                                : (value) {
                                    setState(() {
                                      isTurbo = value;
                                    });
                                  },
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: loadingAnalyze ? null : analyzeData,
            icon: loadingAnalyze
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2.3),
                  )
                : const Icon(Icons.analytics_rounded),
            label: const Text('Analyze'),
          ),
        ],
      ),
    );
  }

  Widget buildResultCard() {
    final hasResult =
        stage1GainPercent != null ||
        potentialClass != null ||
        estimatedHpAfterStage1 != null;

    if (errorMessage != null) {
      return _SectionPanel(
        icon: Icons.error_outline_rounded,
        title: 'A aparut o eroare',
        subtitle: 'Verifica backend-ul si valorile introduse.',
        accentColor: Colors.red,
        child: Text(
          errorMessage!,
          style: const TextStyle(
            color: Color(0xFFB42318),
            fontWeight: FontWeight.w600,
          ),
        ),
      );
    }

    if (!hasResult) {
      return _SectionPanel(
        icon: Icons.auto_graph_rounded,
        title: 'Rezultat analiza',
        subtitle: 'Rezultatele vor aparea aici dupa prima analiza.',
        child: const _EmptyState(
          icon: Icons.insights_rounded,
          text: 'Introdu datele motorului si apasa Analyze.',
        ),
      );
    }

    return _SectionPanel(
      icon: Icons.auto_graph_rounded,
      title: 'Rezultat analiza',
      subtitle: 'Estimare orientativa pentru un setup Stage 1.',
      child: Column(
        children: [
          LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth >= 680;
              final tileWidth = isWide
                  ? (constraints.maxWidth - 28) / 3
                  : constraints.maxWidth;
              return Wrap(
                spacing: 14,
                runSpacing: 14,
                children: [
                  SizedBox(
                    width: tileWidth,
                    child: _MetricTile(
                      icon: Icons.trending_up_rounded,
                      label: 'Stage 1 Gain',
                      value: stage1GainPercent != null
                          ? '${stage1GainPercent!.toStringAsFixed(2)}%'
                          : '-',
                    ),
                  ),
                  SizedBox(
                    width: tileWidth,
                    child: _MetricTile(
                      icon: Icons.workspace_premium_rounded,
                      label: 'Potential',
                      value: potentialClass ?? '-',
                    ),
                  ),
                  SizedBox(
                    width: tileWidth,
                    child: _MetricTile(
                      icon: Icons.bolt_rounded,
                      label: 'HP dupa Stage 1',
                      value: estimatedHpAfterStage1 != null
                          ? estimatedHpAfterStage1!.toStringAsFixed(2)
                          : '-',
                    ),
                  ),
                ],
              );
            },
          ),
          if (derivedFeatures != null) ...[
            const SizedBox(height: 14),
            _DerivedMapSummary(features: derivedFeatures!),
          ],
          if (savedPdfPath != null) ...[
            const SizedBox(height: 14),
            _PathNote(path: savedPdfPath!),
          ],
        ],
      ),
    );
  }

  Widget buildFuelMapPreviewCard() {
    if (fuelMapResult == null) {
      return const SizedBox.shrink();
    }

    final fuelMap = fuelMapResult!['fuel_map'];
    final fuelMapDerived = asStringMap(fuelMapResult!['derived_features']);

    return _SectionPanel(
      icon: Icons.table_chart_rounded,
      title: 'Fuel Map Preview',
      subtitle: 'Date generate pentru vizualizare si raport.',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _StatusChip(
                icon: Icons.workspace_premium_rounded,
                label: 'Potential: ${fuelMapResult!['potential_class']}',
              ),
              if (fuelMapDerived != null)
                _StatusChip(
                  icon: Icons.grid_4x4_rounded,
                  label:
                      'Map: ${fuelMapDerived['rows']}x${fuelMapDerived['columns']}',
                ),
              const _StatusChip(
                icon: Icons.check_circle_rounded,
                label: 'Fuel map generat',
              ),
            ],
          ),
          const SizedBox(height: 14),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFE2E8F0)),
            ),
            child: Text(
              fuelMap.toString(),
              maxLines: 8,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontFamily: 'monospace',
                fontSize: 12.5,
                height: 1.35,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget buildActionButton({
    required String label,
    required IconData icon,
    required Future<void> Function() onPressed,
    required bool isLoading,
  }) {
    return OutlinedButton.icon(
      onPressed: isLoading ? null : onPressed,
      icon: isLoading
          ? const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2.2),
            )
          : Icon(icon),
      label: Text(label),
    );
  }

  Widget buildActions() {
    return _SectionPanel(
      icon: Icons.file_download_done_rounded,
      title: 'Output',
      subtitle: 'Genereaza harta, imaginea heatmap sau raportul PDF.',
      child: LayoutBuilder(
        builder: (context, constraints) {
          final isWide = constraints.maxWidth >= 760;
          final buttonWidth = isWide
              ? (constraints.maxWidth - 24) / 3
              : constraints.maxWidth;

          return Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              SizedBox(
                width: buttonWidth,
                child: buildActionButton(
                  label: 'Generate Fuel Map',
                  icon: Icons.table_chart_rounded,
                  onPressed: generateFuelMap,
                  isLoading: loadingFuelMap,
                ),
              ),
              SizedBox(
                width: buttonWidth,
                child: buildActionButton(
                  label: 'View Heatmap',
                  icon: Icons.image_search_rounded,
                  onPressed: viewHeatmap,
                  isLoading: loadingHeatmap,
                ),
              ),
              SizedBox(
                width: buttonWidth,
                child: buildActionButton(
                  label: 'Generate PDF',
                  icon: Icons.picture_as_pdf_rounded,
                  onPressed: generatePdfReport,
                  isLoading: loadingReport,
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget buildMobileStatusStrip() {
    final gainValue = stage1GainPercent == null
        ? '--'
        : '${stage1GainPercent!.toStringAsFixed(1)}%';
    final hpValue = estimatedHpAfterStage1 == null
        ? '--'
        : estimatedHpAfterStage1!.toStringAsFixed(0);
    final mapValue = fuelMapResult == null ? 'Pending' : 'Ready';

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          _MobileStatChip(
            icon: Icons.trending_up_rounded,
            label: 'Gain',
            value: gainValue,
          ),
          const SizedBox(width: 10),
          _MobileStatChip(
            icon: Icons.bolt_rounded,
            label: 'Stage 1 HP',
            value: hpValue,
          ),
          const SizedBox(width: 10),
          _MobileStatChip(
            icon: Icons.table_chart_rounded,
            label: 'Fuel map',
            value: mapValue,
          ),
        ],
      ),
    );
  }

  Widget buildMobileTabContent(bool busy) {
    switch (mobileTabIndex) {
      case 1:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            buildResultCard(),
            if (fuelMapResult != null) ...[
              const SizedBox(height: 14),
              buildFuelMapPreviewCard(),
            ],
          ],
        );
      case 2:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            buildActions(),
            if (fuelMapResult != null) ...[
              const SizedBox(height: 14),
              buildFuelMapPreviewCard(),
            ],
          ],
        );
      default:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            buildCalibrationAnalyzer(busy),
            const SizedBox(height: 14),
            buildInputForm(busy),
          ],
        );
    }
  }

  Widget buildMobileScaffold(bool busy) {
    return Scaffold(
      body: CustomScrollView(
        keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
        slivers: [
          SliverAppBar(
            pinned: true,
            expandedHeight: 178,
            backgroundColor: const Color(0xFF0F172A),
            foregroundColor: Colors.white,
            title: const Text(
              'ECU AI',
              style: TextStyle(fontWeight: FontWeight.w800),
            ),
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    colors: [Color(0xFF0F172A), Color(0xFF2563EB)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    if (constraints.maxHeight < 158) {
                      return const SizedBox.shrink();
                    }

                    return SafeArea(
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(18, 58, 18, 14),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            const Expanded(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.end,
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Calibration analyzer',
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 22,
                                      fontWeight: FontWeight.w900,
                                    ),
                                  ),
                                  SizedBox(height: 6),
                                  Text(
                                    'Analiza ECU, fuel map si raport PDF.',
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      color: Colors.white70,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 12),
                            const Icon(
                              Icons.memory_rounded,
                              size: 44,
                              color: Colors.white30,
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.only(top: 14),
              child: buildMobileStatusStrip(),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 14, 14, 24),
              child: buildMobileTabContent(busy),
            ),
          ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: mobileTabIndex,
        onDestinationSelected: (index) {
          setState(() {
            mobileTabIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.tune_rounded),
            selectedIcon: Icon(Icons.tune),
            label: 'Date',
          ),
          NavigationDestination(
            icon: Icon(Icons.auto_graph_rounded),
            selectedIcon: Icon(Icons.auto_graph),
            label: 'Rezultat',
          ),
          NavigationDestination(
            icon: Icon(Icons.file_download_done_rounded),
            selectedIcon: Icon(Icons.file_download_done),
            label: 'Output',
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final busy =
        loadingParse ||
        loadingCalibrationAnalyze ||
        loadingAnalyze ||
        loadingFuelMap ||
        loadingHeatmap ||
        loadingReport;
    final isMobile = MediaQuery.sizeOf(context).width < _mobileBreakpoint;

    if (isMobile) {
      return buildMobileScaffold(busy);
    }

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            pinned: true,
            expandedHeight: 168,
            backgroundColor: const Color(0xFF111827),
            foregroundColor: Colors.white,
            flexibleSpace: FlexibleSpaceBar(
              titlePadding: const EdgeInsetsDirectional.only(
                start: 24,
                bottom: 18,
              ),
              title: const Text(
                'ECU Calibration',
                style: TextStyle(fontWeight: FontWeight.w800),
              ),
              background: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    colors: [Color(0xFF111827), Color(0xFF1D4ED8)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: Align(
                  alignment: Alignment.bottomRight,
                  child: Padding(
                    padding: EdgeInsets.fromLTRB(24, 24, 24, 26),
                    child: Icon(
                      Icons.memory_rounded,
                      size: 74,
                      color: Colors.white24,
                    ),
                  ),
                ),
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1080),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(20, 22, 20, 32),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const _IntroBand(),
                      const SizedBox(height: 18),
                      buildCalibrationAnalyzer(busy),
                      const SizedBox(height: 18),
                      buildInputForm(busy),
                      const SizedBox(height: 18),
                      buildResultCard(),
                      const SizedBox(height: 18),
                      buildFuelMapPreviewCard(),
                      if (fuelMapResult != null) const SizedBox(height: 18),
                      buildActions(),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _IntroBand extends StatelessWidget {
  const _IntroBand();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0F0F172A),
            blurRadius: 22,
            offset: Offset(0, 10),
          ),
        ],
      ),
      child: Wrap(
        spacing: 16,
        runSpacing: 14,
        crossAxisAlignment: WrapCrossAlignment.center,
        alignment: WrapAlignment.spaceBetween,
        children: [
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 640),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Calibration analyzer',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                    color: const Color(0xFF0F172A),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Compara fisiere ECU, identifica harti modificate si pastreaza estimarea Stage 1 ca modul secundar.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: const Color(0xFF475569),
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
          const _StatusPill(
            icon: Icons.api_rounded,
            label: 'API local: 127.0.0.1:8000',
          ),
        ],
      ),
    );
  }
}

class _InlineNotice extends StatelessWidget {
  final IconData icon;
  final String text;
  final Color color;

  const _InlineNotice({
    required this.icon,
    required this.text,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.24)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: TextStyle(color: color, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }
}

class _CompactMetric extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _CompactMetric({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 78,
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Row(
        children: [
          Icon(icon, color: const Color(0xFF0F766E)),
          const SizedBox(width: 11),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFF0F172A),
                    fontWeight: FontWeight.w900,
                    fontSize: 18,
                  ),
                ),
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFF64748B),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _FindingRow extends StatelessWidget {
  final Map<String, dynamic> finding;

  const _FindingRow({required this.finding});

  Color get color {
    switch (finding['severity']) {
      case 'high':
        return const Color(0xFFB91C1C);
      case 'medium':
        return const Color(0xFFB45309);
      default:
        return const Color(0xFF0F766E);
    }
  }

  @override
  Widget build(BuildContext context) {
    return _InlineNotice(
      icon: Icons.report_gmailerrorred_rounded,
      color: color,
      text:
          '${finding['map_name']} (${finding['category']}): ${finding['message']}',
    );
  }
}

class _PowerEstimatePanel extends StatelessWidget {
  final Map<String, dynamic> estimate;

  const _PowerEstimatePanel({required this.estimate});

  String _value(String key, {String suffix = ''}) {
    final value = estimate[key];
    if (value is num) {
      return '${value.toStringAsFixed(value % 1 == 0 ? 0 : 2)}$suffix';
    }
    return value == null ? '-' : '$value$suffix';
  }

  @override
  Widget build(BuildContext context) {
    final available = estimate['available'] == true;
    if (!available) {
      return _InlineNotice(
        icon: Icons.speed_rounded,
        text:
            estimate['reason']?.toString() ??
            'Estimarea de putere nu este disponibila.',
        color: const Color(0xFF64748B),
      );
    }

    final derived = Map<String, dynamic>.from(
      (estimate['derived_inputs'] as Map?) ?? {},
    );

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Icon(Icons.speed_rounded, color: Color(0xFF0F766E)),
              const SizedBox(width: 9),
              Expanded(
                child: Text(
                  'Power estimate from calibration',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              _StatusChip(
                icon: Icons.verified_rounded,
                label: 'Confidence: ${estimate['confidence']}',
              ),
            ],
          ),
          const SizedBox(height: 12),
          LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth >= 720;
              final width = isWide
                  ? (constraints.maxWidth - 20) / 3
                  : constraints.maxWidth;
              return Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  SizedBox(
                    width: width,
                    child: _CompactMetric(
                      icon: Icons.trending_up_rounded,
                      label: 'Stage 1 gain',
                      value: _value('stage1_gain_percent', suffix: '%'),
                    ),
                  ),
                  SizedBox(
                    width: width,
                    child: _CompactMetric(
                      icon: Icons.bolt_rounded,
                      label: 'Estimated HP',
                      value: _value('estimated_hp_after_stage1', suffix: ' hp'),
                    ),
                  ),
                  SizedBox(
                    width: width,
                    child: _CompactMetric(
                      icon: Icons.category_rounded,
                      label: 'Potential',
                      value: _value('potential_class'),
                    ),
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _StatusChip(
                icon: Icons.speed_rounded,
                label: 'RPM: ${derived['rpm'] ?? '-'}',
              ),
              _StatusChip(
                icon: Icons.compress_rounded,
                label: 'Boost: ${derived['boost_pressure'] ?? '-'} bar',
              ),
              _StatusChip(
                icon: Icons.local_gas_station_rounded,
                label: 'IQ: ${derived['injection_quantity'] ?? '-'} mg',
              ),
              _StatusChip(
                icon: Icons.air_rounded,
                label: 'AFR: ${derived['afr'] ?? '-'}',
              ),
            ],
          ),
          if (estimate['note'] != null) ...[
            const SizedBox(height: 10),
            Text(
              estimate['note'].toString(),
              style: const TextStyle(
                color: Color(0xFF64748B),
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _RecommendationPanel extends StatelessWidget {
  final List<dynamic> items;

  const _RecommendationPanel({required this.items});

  @override
  Widget build(BuildContext context) {
    final recommendations = items
        .map((item) => Map<String, dynamic>.from(item as Map))
        .take(6)
        .toList();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Icon(Icons.tips_and_updates_rounded, size: 20),
              const SizedBox(width: 9),
              Expanded(
                child: Text(
                  'Power Improvement Suggestions',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          for (final recommendation in recommendations) ...[
            _RecommendationTile(item: recommendation),
            if (recommendation != recommendations.last)
              const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }
}

class _RecommendationTile extends StatelessWidget {
  final Map<String, dynamic> item;

  const _RecommendationTile({required this.item});

  Color get accent {
    switch (item['risk']) {
      case 'high':
      case 'medium-high':
        return const Color(0xFFB45309);
      case 'unknown':
        return const Color(0xFF64748B);
      default:
        return const Color(0xFF0F766E);
    }
  }

  @override
  Widget build(BuildContext context) {
    final maps = item['maps'] is List ? (item['maps'] as List) : const [];
    final checks = item['checks'] is List ? (item['checks'] as List) : const [];

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: accent.withValues(alpha: 0.24)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.auto_fix_high_rounded, color: accent, size: 20),
              const SizedBox(width: 9),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item['title']?.toString() ?? 'Suggestion',
                      style: const TextStyle(
                        color: Color(0xFF0F172A),
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      item['reason']?.toString() ?? '-',
                      style: const TextStyle(
                        color: Color(0xFF475569),
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _StatusChip(
                icon: Icons.trending_up_rounded,
                label: '${item['suggested_change']}',
              ),
              _StatusChip(
                icon: Icons.location_searching_rounded,
                label: '${item['target_zone']}',
              ),
              _StatusChip(
                icon: Icons.health_and_safety_rounded,
                label: 'Risk: ${item['risk']}',
              ),
              _StatusChip(
                icon: Icons.verified_rounded,
                label: 'Confidence: ${item['confidence']}',
              ),
            ],
          ),
          if (maps.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              'Maps: ${maps.take(4).join(', ')}',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: Color(0xFF334155),
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
          if (checks.isNotEmpty) ...[
            const SizedBox(height: 8),
            for (final check in checks.take(3))
              Padding(
                padding: const EdgeInsets.only(bottom: 3),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.check_rounded,
                      size: 16,
                      color: Color(0xFF0F766E),
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        '$check',
                        style: const TextStyle(color: Color(0xFF475569)),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ],
      ),
    );
  }
}

class _MapBrowser extends StatelessWidget {
  final List<dynamic> items;

  const _MapBrowser({required this.items});

  List<Map<String, dynamic>> get sortedItems {
    final maps = items
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
    maps.sort((left, right) {
      final leftDiff = Map<String, dynamic>.from((left['diff'] as Map?) ?? {});
      final rightDiff = Map<String, dynamic>.from(
        (right['diff'] as Map?) ?? {},
      );
      final leftChanged = ((leftDiff['changed_cells'] as num?) ?? 0).toInt();
      final rightChanged = ((rightDiff['changed_cells'] as num?) ?? 0).toInt();
      return rightChanged.compareTo(leftChanged);
    });
    return maps;
  }

  @override
  Widget build(BuildContext context) {
    final maps = sortedItems;

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 6),
            child: Row(
              children: [
                const Icon(Icons.view_list_rounded, size: 20),
                const SizedBox(width: 9),
                Expanded(
                  child: Text(
                    'Map Browser',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
                Text(
                  '${maps.length} maps',
                  style: const TextStyle(
                    color: Color(0xFF64748B),
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          for (final item in maps.take(25)) _MapBrowserTile(item: item),
        ],
      ),
    );
  }
}

class _MapBrowserTile extends StatelessWidget {
  final Map<String, dynamic> item;

  const _MapBrowserTile({required this.item});

  @override
  Widget build(BuildContext context) {
    final diff = Map<String, dynamic>.from((item['diff'] as Map?) ?? {});
    final changedCells = ((diff['changed_cells'] as num?) ?? 0).toInt();
    final changedPercent = diff['changed_percent'] ?? 0;
    final hasModified = item['modified_preview'] != null;

    return ExpansionTile(
      tilePadding: const EdgeInsets.symmetric(horizontal: 14),
      childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
      leading: Icon(
        changedCells > 0 ? Icons.difference_rounded : Icons.table_rows_rounded,
        color: changedCells > 0
            ? const Color(0xFF0F766E)
            : const Color(0xFF64748B),
      ),
      title: Text(
        item['name']?.toString() ?? 'Map',
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(fontWeight: FontWeight.w900),
      ),
      subtitle: Text(
        '${item['address_hex']} | ${item['rows']}x${item['columns']} | ${item['data_type']} | ${item['category']}',
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      trailing: SizedBox(
        width: 76,
        child: Text(
          hasModified ? '$changedPercent%' : 'view',
          textAlign: TextAlign.end,
          style: TextStyle(
            color: changedCells > 0
                ? const Color(0xFF0F766E)
                : const Color(0xFF64748B),
            fontWeight: FontWeight.w900,
          ),
        ),
      ),
      children: [
        _MapMetricStrip(item: item, diff: diff),
        const SizedBox(height: 10),
        _MapPreviewGrid(title: 'Original preview', rows: item['preview']),
        if (hasModified) ...[
          const SizedBox(height: 10),
          _MapPreviewGrid(
            title: 'Modified preview',
            rows: item['modified_preview'],
          ),
        ],
        if (item['delta_preview'] != null) ...[
          const SizedBox(height: 10),
          _MapPreviewGrid(
            title: 'Delta preview',
            rows: item['delta_preview'],
            highlightDelta: true,
          ),
        ],
      ],
    );
  }
}

class _MapMetricStrip extends StatelessWidget {
  final Map<String, dynamic> item;
  final Map<String, dynamic> diff;

  const _MapMetricStrip({required this.item, required this.diff});

  @override
  Widget build(BuildContext context) {
    final summary = Map<String, dynamic>.from((item['summary'] as Map?) ?? {});
    final modifiedSummary = Map<String, dynamic>.from(
      (item['modified_summary'] as Map?) ?? {},
    );
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        _StatusChip(
          icon: Icons.memory_rounded,
          label: '${item['address_hex']} / ${item['bytes']} bytes',
        ),
        _StatusChip(
          icon: Icons.analytics_rounded,
          label: 'Orig mean: ${summary['mean'] ?? '-'}',
        ),
        if (modifiedSummary.isNotEmpty)
          _StatusChip(
            icon: Icons.compare_arrows_rounded,
            label: 'Mod mean: ${modifiedSummary['mean'] ?? '-'}',
          ),
        if (diff.isNotEmpty)
          _StatusChip(
            icon: Icons.functions_rounded,
            label: 'Delta max: ${diff['max_abs_delta'] ?? '-'}',
          ),
      ],
    );
  }
}

class _MapPreviewGrid extends StatelessWidget {
  final String title;
  final dynamic rows;
  final bool highlightDelta;

  const _MapPreviewGrid({
    required this.title,
    required this.rows,
    this.highlightDelta = false,
  });

  @override
  Widget build(BuildContext context) {
    final tableRows = rows is List ? rows!.cast<dynamic>() : <dynamic>[];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            color: Color(0xFF334155),
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 6),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Container(
            decoration: BoxDecoration(
              border: Border.all(color: const Color(0xFFE2E8F0)),
              borderRadius: BorderRadius.circular(8),
              color: Colors.white,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final row in tableRows)
                  Row(
                    children: [
                      for (final value in (row is List ? row : const []))
                        _MapValueCell(
                          value: value,
                          highlightDelta: highlightDelta,
                        ),
                    ],
                  ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _MapValueCell extends StatelessWidget {
  final dynamic value;
  final bool highlightDelta;

  const _MapValueCell({required this.value, required this.highlightDelta});

  @override
  Widget build(BuildContext context) {
    final number = value is num ? value.toDouble() : null;
    final text = number == null
        ? '$value'
        : number.toStringAsFixed(number.abs() >= 100 ? 1 : 3);
    final color = !highlightDelta || number == null || number == 0
        ? Colors.white
        : number > 0
        ? const Color(0xFFEFF6FF)
        : const Color(0xFFFFF1F2);

    return Container(
      width: 76,
      height: 34,
      alignment: Alignment.centerRight,
      padding: const EdgeInsets.symmetric(horizontal: 8),
      decoration: BoxDecoration(
        color: color,
        border: const Border(
          right: BorderSide(color: Color(0xFFE2E8F0)),
          bottom: BorderSide(color: Color(0xFFE2E8F0)),
        ),
      ),
      child: Text(
        text,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(
          fontFamily: 'monospace',
          fontSize: 12,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _MobileStatChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _MobileStatChip({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 136,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0D0F172A),
            blurRadius: 16,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: Theme.of(
                context,
              ).colorScheme.primary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(
              icon,
              size: 19,
              color: Theme.of(context).colorScheme.primary,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFF0F172A),
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 1),
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFF64748B),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionPanel extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Widget child;
  final Color? accentColor;

  const _SectionPanel({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.child,
    this.accentColor,
  });

  @override
  Widget build(BuildContext context) {
    final color = accentColor ?? Theme.of(context).colorScheme.primary;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0D0F172A),
            blurRadius: 18,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: color),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: const Color(0xFF64748B),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          child,
        ],
      ),
    );
  }
}

class _MetricTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _MetricTile({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 116,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: Theme.of(context).colorScheme.primary),
          const Spacer(),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w900,
              color: const Color(0xFF0F172A),
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: const Color(0xFF64748B),
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _DerivedMapSummary extends StatelessWidget {
  final Map<String, dynamic> features;

  const _DerivedMapSummary({required this.features});

  String _value(String key, {String suffix = ''}) {
    final value = features[key];
    if (value == null) return '-';
    if (value is num) {
      return '${value.toStringAsFixed(value % 1 == 0 ? 0 : 2)}$suffix';
    }
    return '$value$suffix';
  }

  @override
  Widget build(BuildContext context) {
    final rows = features['rows'] ?? '-';
    final columns = features['columns'] ?? '-';

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Wrap(
        spacing: 10,
        runSpacing: 10,
        children: [
          _StatusChip(
            icon: Icons.grid_on_rounded,
            label: '$rows x $columns ${_value('map_type')}',
          ),
          _StatusChip(
            icon: Icons.speed_rounded,
            label: 'RPM: ${_value('rpm')}',
          ),
          _StatusChip(
            icon: Icons.local_gas_station_rounded,
            label: 'IQ: ${_value('injection_quantity', suffix: ' mg')}',
          ),
          _StatusChip(
            icon: Icons.compress_rounded,
            label: 'Boost: ${_value('boost_pressure', suffix: ' bar')}',
          ),
          _StatusChip(icon: Icons.air_rounded, label: 'AFR: ${_value('afr')}'),
          _StatusChip(
            icon: Icons.functions_rounded,
            label: 'Range: ${_value('min_value')} .. ${_value('max_value')}',
          ),
        ],
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  final IconData icon;
  final String label;

  const _StatusPill({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFECFDF5),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFFA7F3D0)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: const Color(0xFF047857)),
          const SizedBox(width: 8),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF065F46),
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  final IconData icon;
  final String label;

  const _StatusChip({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Chip(
      avatar: Icon(icon, size: 18),
      label: Text(label),
      side: const BorderSide(color: Color(0xFFD9E0EC)),
      backgroundColor: Colors.white,
      labelStyle: const TextStyle(fontWeight: FontWeight.w600),
    );
  }
}

class _PathNote extends StatelessWidget {
  final String path;

  const _PathNote({required this.path});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Row(
        children: [
          const Icon(Icons.picture_as_pdf_rounded, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              path,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _ImportedMapNote extends StatelessWidget {
  final String fileName;
  final bool isBinary;

  const _ImportedMapNote({required this.fileName, this.isBinary = false});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Row(
        children: [
          const Icon(Icons.description_rounded, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              fileName,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(width: 10),
          _StatusChip(
            icon: isBinary ? Icons.memory_rounded : Icons.check_circle_rounded,
            label: isBinary ? 'Binary ECU' : 'Parsed',
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  final IconData icon;
  final String text;

  const _EmptyState({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        children: [
          Icon(icon, color: const Color(0xFF64748B), size: 30),
          const SizedBox(height: 8),
          Text(
            text,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Color(0xFF475569),
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
