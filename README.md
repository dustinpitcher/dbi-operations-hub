# 🏢 DBI Operations Hub

A comprehensive business operations platform for Dirty Bird Industries, providing integrated tools for inventory management, assembly planning, purchase order generation, and future business modules.

## 🌐 **Live Application**: https://dbi-operations-hub.azurewebsites.net

## 📊 **Current Modules**

### 🏭 **Assembly Management**
- **Assembly Analysis**: Determine which products can be assembled based on component availability
- **Transfer Recommendations**: Identify items to move between NC warehouses based on sales velocity
- **30-Day Inventory Target**: Proactive recommendations to maintain optimal stock levels
- **Excel Reports**: Professional multi-sheet reports with assembly and transfer recommendations

### 💰 **Purchase Order Generation**  
- **Automated PO Creation**: Generate weekly purchase orders for NC and CA warehouses
- **Profit-Based Velocity**: Intelligent ordering based on profit margins and sales velocity
- **Supplier Management**: Built-in exclusion system for problematic vendors
- **Cin7 Core Integration**: Direct CSV import format for seamless workflow

## 🚀 **Platform Features**

### **Unified Business Hub**
- **Single Entry Point**: Access all business operations from one application
- **Modular Architecture**: Easy to add new business functions
- **Consistent UI/UX**: Professional interface across all modules
- **Cost Optimized**: Single Azure deployment reduces operational costs by 50%

### **Future-Ready Design**
- **Extensible Module System**: Framework ready for Sales Analytics, HR Management, Quality Control
- **Shared Resources**: Common templates, authentication, and utilities
- **Scalable Infrastructure**: Built to handle growing business operations

## 🛠️ **Module Structure**

```
dbi-operations-hub/
├── app.py                    # Main Flask application
├── config.py                 # Configuration management
├── requirements.txt          # Dependencies
├── modules/                  # Business modules
│   ├── __init__.py
│   ├── assembly/            # Assembly management module
│   ├── purchase_orders/     # PO generation module
│   └── [future_modules]/    # HR, Sales, Analytics, etc.
├── templates/               # Jinja2 templates
│   ├── base.html           # Shared template foundation
│   ├── index.html          # Main dashboard
│   └── modules/            # Module-specific templates
├── static/                 # CSS, JS, images
└── uploads/                # File upload storage
```

## 🎯 **Business Value**

### **Immediate Benefits**
- ✅ **Cost Reduction**: 50% savings on Azure hosting costs
- ✅ **Operational Efficiency**: Centralized access to business tools
- ✅ **Professional Interface**: Consistent, enterprise-grade user experience
- ✅ **Reduced Maintenance**: Single codebase to maintain and deploy

### **Strategic Advantages**
- ✅ **Scalable Platform**: Ready for additional business modules
- ✅ **Unified Data**: Potential for cross-module insights and reporting
- ✅ **Single Sign-On Ready**: Framework for centralized authentication
- ✅ **Mobile Responsive**: Works seamlessly across all devices

## 💰 **Cost Optimization**

### **Previous Architecture**: $36-38/month
- Assembly Generation App: ~$18/month
- PO Generation App: ~$18/month

### **New Architecture**: $18-19/month
- Single Operations Hub: ~$18/month
- **Savings**: 50% reduction in hosting costs

Built with the **Rapid Application Development** paradigm for maximum business efficiency.
