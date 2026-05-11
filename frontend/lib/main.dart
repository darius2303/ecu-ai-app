import 'dart:io';
import 'dart:typed_data';

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
  final api = ApiService();

  final rpmController = TextEditingController();
  final boostController = TextEditingController();
  final injectionController = TextEditingController();
  final afrController = TextEditingController();
  final displacementController = TextEditingController();
  final stockHpController = TextEditingController();

  String fuelType = 'diesel';
  bool isTurbo = true;

  bool loadingAnalyze = false;
  bool loadingFuelMap = false;
  bool loadingHeatmap = false;
  bool loadingReport = false;

  String? errorMessage;

  double? stage1GainPercent;
  String? potentialClass;
  double? estimatedHpAfterStage1;

  Map<String, dynamic>? fuelMapResult;
  Uint8List? heatmapBytes;
  String? savedPdfPath;

  Map<String, dynamic> buildInputData() {
    return {
      'rpm': double.tryParse(rpmController.text) ?? 0,
      'boost_pressure': double.tryParse(boostController.text) ?? 0,
      'injection_quantity': double.tryParse(injectionController.text) ?? 0,
      'afr': double.tryParse(afrController.text) ?? 0,
      'engine_displacement': double.tryParse(displacementController.text) ?? 0,
      'fuel_type': fuelType,
      'is_turbo': isTurbo,
      'stock_hp': stockHpController.text.trim().isEmpty
          ? null
          : double.tryParse(stockHpController.text),
    };
  }

  Future<void> analyzeData() async {
    FocusScope.of(context).unfocus();

    setState(() {
      loadingAnalyze = true;
      errorMessage = null;
    });

    try {
      final result = await api.analyze(buildInputData());

      setState(() {
        stage1GainPercent = (result['stage1_gain_percent'] as num?)?.toDouble();
        potentialClass = result['potential_class']?.toString();
        estimatedHpAfterStage1 = (result['estimated_hp_after_stage1'] as num?)
            ?.toDouble();
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

  Widget buildInputForm(bool busy) {
    final fields = [
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
      title: 'Date motor',
      subtitle: 'Introdu valorile ECU pentru estimarea Stage 1.',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth >= 680;
              return Wrap(
                spacing: 14,
                runSpacing: 14,
                children: [
                  for (final field in fields)
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

  @override
  Widget build(BuildContext context) {
    final busy =
        loadingAnalyze || loadingFuelMap || loadingHeatmap || loadingReport;

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
                'ECU AI App',
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
                  'Stage 1 estimator',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                    color: const Color(0xFF0F172A),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Analizeaza date ECU, estimeaza castigul si genereaza rapid fuel map, heatmap si raport PDF.',
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
